from typing import Optional

import cv2
from collections import Counter, defaultdict

from lib.image_processing import load_image, to_grayscale, binarize_otsu, binarize_adaptive
from lib.barcode_detection import detect_barcode_candidates
from lib.scanline import scanline_to_runs, trim_white_runs, runs_to_bits
from lib.decoder import decode_ean13_bits
from lib.pattern_decoder import decode_ean13_from_runs


class BarcodeReadError(ValueError):
    def __init__(self, message: str, reasons: Optional[list[str]] = None):
        super().__init__(message)
        self.reasons = reasons or []

    def __str__(self):
        if not self.reasons:
            return super().__str__()

        details = "\n".join(f"  - {reason}" for reason in self.reasons[:12])
        remaining = len(self.reasons) - 12
        if remaining > 0:
            details += f"\n  - ... további {remaining} hasonló hiba"

        return f"{super().__str__()}\nLeggyakoribb okok:\n{details}"


def estimate_module_width_from_total(runs):
    total_width = sum(length for _, length in runs)
    return total_width / 95


def normalize_to_95_bits(bits: str) -> str:
    if len(bits) < 80:
        raise ValueError(f"Túl rövid bitstring: {len(bits)} bit, legalább kb. 80 kell.")

    result = ""

    for i in range(95):
        index = int(i * len(bits) / 95)
        result += bits[index]

    return result


def get_scan_y_positions(height, count=80):
    # A széleken gyakran van zaj / perspektíva miatti torzulás, ezért a teljes magasság
    # helyett inkább a középső 80%-ot sűrűn mintavételezzük.
    if height <= 1:
        return [0]

    start = int(height * 0.10)
    end = max(start, int(height * 0.90))

    step = (end - start) / max(1, count - 1)

    return sorted(set(int(start + i * step) for i in range(count)))


def is_valid_ean_structure(bits: str) -> bool:
    return (
        len(bits) == 95
        and bits[0:3] == "101"
        and bits[45:50] == "01010"
        and bits[92:95] == "101"
    )


def _try_decode_scanline_once(scanline):
    runs = scanline_to_runs(scanline)
    runs = trim_white_runs(runs)

    if len(runs) < 50:
        raise ValueError(f"Túl kevés run a scanline-on: {len(runs)} < 50.")

    # Elsődleges: run-length mintaillesztés, ez általában pontosabb, mint bitre kerekíteni.
    try:
        result, score = decode_ean13_from_runs(runs)
        confidence = 1 / (1 + score)
        return result, confidence, "run"
    except Exception as run_error:
        run_error_message = str(run_error)

    # Fallback: run -> becsült 95 bites sorozat -> klasszikus EAN-13 bit dekódolás.
    try:
        module_width = estimate_module_width_from_total(runs)
        if module_width <= 0:
            raise ValueError("A becsült modul-szélesség nulla vagy negatív.")

        bits = runs_to_bits(runs, module_width)
        bits = normalize_to_95_bits(bits)

        if not is_valid_ean_structure(bits):
            raise ValueError(
                f"Érvénytelen guard bitstruktúra: start={bits[0:3]}, "
                f"middle={bits[45:50]}, end={bits[92:95]}."
            )

        result = decode_ean13_bits(bits)
        return result, 0.25, "bits"

    except Exception as bit_error:
        raise ValueError(f"Run dekódolás hiba: {run_error_message}; bit fallback hiba: {bit_error}")


def try_decode_scanline(scanline, diagnostics: Optional[list[str]] = None):
    errors = []

    # Balról jobbra és jobbról balra is megpróbáljuk. Normál képnél az első nyer,
    # tükrözött / rosszul kivágott ROI esetén a fordított scanline menthet találatot.
    for direction, candidate in (("balról jobbra", scanline), ("jobbról balra", scanline[::-1])):
        try:
            value, confidence, method = _try_decode_scanline_once(candidate)
            if direction == "jobbról balra":
                confidence *= 0.92
            return value, confidence, method
        except Exception as error:
            errors.append(f"{direction}: {error}")

    if diagnostics is not None and errors:
        diagnostics.extend(errors)

    return None


def _binary_variants(gray):
    variants = [
        ("adaptive", binarize_adaptive(gray)),
        ("otsu", binarize_otsu(gray)),
    ]

    # Néha a kontraszt / előfeldolgozás miatt invertált irányból stabilabb a run-sor.
    # Az EAN dekóder a fekete sávot 1-nek várja, ezért ezt külön, gyengébb fallbackként próbáljuk.
    variants.extend([
        ("adaptive_inverted", cv2.bitwise_not(variants[0][1])),
        ("otsu_inverted", cv2.bitwise_not(variants[1][1])),
    ])

    return variants


def try_decode_roi(roi, diagnostics: Optional[list[str]] = None):
    gray = to_grayscale(roi)

    results = []
    band_heights = [1, 3, 5]

    for binary_name, binary in _binary_variants(gray):
        height = binary.shape[0]

        for band_height in band_heights:
            for y in get_scan_y_positions(height, count=90):
                y1 = max(0, y - band_height // 2)
                y2 = min(height, y + band_height // 2 + 1)

                band = binary[y1:y2, :]
                scanline = band.mean(axis=0)

                res = try_decode_scanline(scanline, diagnostics=diagnostics)

                if res:
                    value, confidence, method = res
                    # Az invertált binarizálás fallback, ezért kicsit kisebb súlyt kap.
                    if binary_name.endswith("_inverted"):
                        confidence *= 0.85
                    if band_height == 1:
                        confidence *= 0.95
                    results.append((value, confidence, f"{binary_name}/{method}/band{band_height}"))

    return results


# Kép forgatása az alábbi fokokban: 0, 90, 180, 270
def generate_image_variants(image):
    return [
        ("0°", image),
        ("90°", cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)),
        ("180°", cv2.rotate(image, cv2.ROTATE_180)),
        ("270°", cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)),
    ]


def _summarize_failures(errors: list[str], limit=10) -> list[str]:
    if not errors:
        return ["Nem találtam dekódolható EAN-13 mintát egyik ROI-ban / scanline-ban sem."]

    categories = Counter()
    examples = {}

    for error in errors:
        text = error.strip()

        if "Túl kevés run" in text:
            key = "Túl kevés fekete-fehér váltás látszik a scanline-on; valószínűleg nem a vonalkódon fut át a vizsgált sor, vagy túl zajos / elmosódott a kivágás."
        elif "Start guard" in text:
            key = "A start guard nem olvasható stabilan; a vonalkód bal széle hiányzik, ferde, vagy túl zajos."
        elif "Middle guard" in text:
            key = "A középső guard minta hibás; a scanline nem pontosan a barcode sávjain megy keresztül, vagy perspektíva/blur torzítja."
        elif "End guard" in text:
            key = "Az end guard nem olvasható stabilan; a vonalkód jobb széle hiányzik vagy torz."
        elif "Hibás checksum" in text:
            key = "A dekódolt 13 számjegy checksumja hibás; legalább egy számjegy rosszul lett leolvasva."
        elif "Bizonytalan számjegy-minta" in text or "Gyenge számjegy-minta" in text:
            key = "Egy vagy több számjegy run-aránya túl gyenge/bizonytalan; a kép valószínűleg életlen, túl kicsi vagy ferde."
        elif "Érvénytelen parity" in text:
            key = "A bal oldali L/G parity minta érvénytelen; a scanner rossz kezdőpontot vagy hamis csíkos mintát talált."
        elif "guard bitstruktúra" in text:
            key = "A 95 bites EAN szerkezet guard mintái nem stimmelnek; a fallback bit-dekóder nem talált szabályos EAN-13 struktúrát."
        else:
            key = text

        categories[key] += 1
        examples.setdefault(key, text)

    result = []
    for reason, count in categories.most_common(limit):
        example = examples.get(reason, "")
        if reason == example or len(example) > 180:
            result.append(f"{reason} ({count}×)")
        else:
            result.append(f"{reason} Példa: {example} ({count}×)")

    return result




def _method_families(method_counter: Counter) -> set[str]:
    """
    adaptive/run/band3 -> adaptive
    otsu/bits/band5    -> otsu
    adaptive_inverted/... -> adaptive_inverted
    """
    families = set()
    for method in method_counter:
        families.add(method.split("/", 1)[0])
    return families


def _is_inverted_only(method_counter: Counter) -> bool:
    families = _method_families(method_counter)
    return bool(families) and all(name.endswith("_inverted") for name in families)


def _candidate_quality(value: str, score: float, hits: int, methods: Counter, second_score: float) -> tuple[bool, list[str]]:
    """
    A checksum önmagában kevés: véletlen csíkos mintákból is kijöhet checksum-helyes EAN.
    Ezért a végső kódot csak akkor fogadjuk el, ha több scanline / módszer is támogatja,
    vagy nagyon erős a pontszáma.
    """
    reasons = []
    families = _method_families(methods)
    dominance = float("inf") if second_score <= 0 else score / second_score

    if _is_inverted_only(methods):
        reasons.append(
            "A legjobb jelölt csak invertált képfeldolgozásból jött. Ez gyakran hamis pozitív zajos képeknél."
        )

    # Nagyon erős konszenzus: sok scanline és magas összpontszám.
    if score >= 50 and hits >= 20 and not _is_inverted_only(methods):
        return True, []

    # Közepesen erős konszenzus: elfogadható, ha nem áll túl közel más jelölthöz.
    if score >= 20 and hits >= 10 and dominance >= 2.5 and not _is_inverted_only(methods):
        return True, []

    # Alacsony pontszámú jelöltet csak akkor engedünk át, ha tényleg stabil:
    # legalább 6 scanline támogatja, és vagy több threshold család is látja,
    # vagy az első jelölt sokkal erősebb, mint a második.
    if score >= 7 and hits >= 6 and not _is_inverted_only(methods):
        if len(families) >= 2:
            return True, []
        if dominance >= 4.0:
            return True, []

    if hits < 6:
        reasons.append(f"Túl kevés scanline támogatta a jelöltet: {hits} találat, minimum kb. 6 kell.")
    if score < 7:
        reasons.append(f"Túl alacsony összpontszám: {score:.2f}, minimum kb. 7 kell.")
    if second_score > 0 and dominance < 4.0 and score < 20:
        reasons.append(
            f"A legjobb jelölt nem elég domináns: best/second arány {dominance:.2f}, alacsony score-nál kb. 4.0 kell."
        )
    if len(families) < 2 and score < 20:
        reasons.append(
            f"Csak egy binarizálási család támogatta ({', '.join(sorted(families)) or 'nincs'}); "
            "alacsony score-nál ez könnyen hamis pozitív."
        )

    if not reasons:
        reasons.append("A jelölt checksum-helyes volt, de nem volt elég stabil több scanline / módszer alapján.")

    return False, reasons


def read_ean13_from_image(path: str, *, return_debug: bool = False):
    image = load_image(path)

    score_map = defaultdict(float)
    hit_count = defaultdict(int)
    method_map = defaultdict(Counter)
    errors = []
    roi_count = 0

    for variant_name, variant in generate_image_variants(image):
        rois = detect_barcode_candidates(variant, max_candidates=20)
        if not rois:
            errors.append(f"{variant_name}: nem találtam barcode-gyanús területet.")
            continue

        for roi_index, roi in enumerate(rois, start=1):
            roi_count += 1
            roi_errors = []
            results = []

            # A ROI detektor nem mindig tudja biztosan, hogy a kivágott barcode
            # 0 vagy 90 fokban áll. Ezért a kivágást magát is megpróbáljuk több
            # irányból, de a 90/270 fokos ROI-próbák kicsit kisebb súlyt kapnak.
            roi_variants = [
                ("roi0", roi, 1.00),
                ("roi90", cv2.rotate(roi, cv2.ROTATE_90_CLOCKWISE), 0.92),
                ("roi270", cv2.rotate(roi, cv2.ROTATE_90_COUNTERCLOCKWISE), 0.92),
                ("roi180", cv2.rotate(roi, cv2.ROTATE_180), 0.96),
            ]

            for roi_variant_name, roi_variant, roi_weight in roi_variants:
                partial = try_decode_roi(roi_variant, diagnostics=roi_errors)
                for value, confidence, method in partial:
                    results.append((value, confidence * roi_weight, f"{roi_variant_name}/{method}"))

            if not results:
                # ROI-nként csak pár tipikus hibát emelünk át, különben túl nagy lenne a kimenet.
                for reason in _summarize_failures(roi_errors, limit=3):
                    errors.append(f"{variant_name} ROI#{roi_index}: {reason}")
                continue

            for value, confidence, method in results:
                score_map[value] += confidence
                hit_count[value] += 1
                method_map[value][method] += 1

    if not score_map:
        summary = _summarize_failures(errors, limit=12)
        raise BarcodeReadError(
            f"Nem sikerült EAN-13 kódot olvasni. Vizsgált ROI-k száma: {roi_count}.",
            reasons=summary,
        )

    ranked = sorted(score_map.items(), key=lambda item: item[1], reverse=True)
    best_value, best_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0

    alternatives = ", ".join(f"{value}: {score:.2f}" for value, score in ranked[:5])

    # Ha több különböző checksum-helyes kód is közel azonos pontszámot kap, jobb ezt
    # bizonytalannak jelezni, mint rossz kódot visszaadni. A régi 0.82 túl laza volt:
    # több logolt ROSSZ esetben 2-3× különbség mellett is hamis kód nyert.
    if second_score > 0 and second_score / best_score > 0.40:
        raise BarcodeReadError(
            "Bizonytalan EAN-13 olvasás: több eltérő kód is checksum-helyes és nem elég nagy köztük a különbség.",
            reasons=[
                f"Jelöltek: {alternatives}",
                f"Best/second arány: {best_score / second_score:.2f}. Legalább kb. 2.5 kell erős, vagy kb. 4.0 gyenge jelöltnél.",
                "Ez általában ferde, életlen, túl kis felbontású vagy rosszul kivágott vonalkódnál történik.",
            ],
        )

    accepted, quality_reasons = _candidate_quality(
        best_value,
        best_score,
        hit_count[best_value],
        method_map[best_value],
        second_score,
    )

    if not accepted:
        raise BarcodeReadError(
            "Bizonytalan EAN-13 olvasás: a checksum-helyes jelölt nem kapott elég erős támogatást.",
            reasons=[
                f"Legjobb jelölt: {best_value}, score={best_score:.2f}, találatok={hit_count[best_value]}, módszerek={dict(method_map[best_value])}.",
                *quality_reasons,
                f"Jelöltek: {alternatives}" if alternatives else "Nem volt más checksum-helyes alternatíva.",
            ],
        )

    if return_debug:
        return {
            "value": best_value,
            "score": best_score,
            "hits": hit_count[best_value],
            "methods": dict(method_map[best_value]),
            "alternatives": ranked[1:6],
            "roi_count": roi_count,
            "quality": "accepted",
        }

    return best_value
