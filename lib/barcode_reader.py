import cv2
from collections import defaultdict

from lib.image_processing import load_image, to_grayscale, binarize_otsu, binarize_adaptive
from lib.barcode_detection import detect_barcode_candidates
from lib.scanline import scanline_to_runs, trim_white_runs, runs_to_bits
from lib.decoder import decode_ean13_bits
from lib.pattern_decoder import decode_ean13_from_runs


def estimate_module_width_from_total(runs):
    total_width = sum(length for _, length in runs)
    return total_width / 95


def normalize_to_95_bits(bits: str) -> str:
    if len(bits) < 80:
        raise ValueError("Túl rövid bitstring.")

    result = ""

    for i in range(95):
        index = int(i * len(bits) / 95)
        result += bits[index]

    return result


def get_scan_y_positions(height, count=40):
    start = 0
    end = height - 1

    step = (end - start) / max(1, count - 1)

    return [int(start + i * step) for i in range(count)]


def is_valid_ean_structure(bits: str) -> bool:
    if len(bits) != 95:
        return False

    if bits[0:3] != "101":
        return False

    if bits[45:50] != "01010":
        return False

    if bits[92:95] != "101":
        return False

    return True


def try_decode_scanline(scanline):
    runs = scanline_to_runs(scanline)
    runs = trim_white_runs(runs)

    # run decoder
    try:
        result, score = decode_ean13_from_runs(runs)

        # minél kisebb a score, annál jobb
        confidence = 1 / (1 + score)

        return result, confidence

    except Exception:
        pass

    # fallback
    try:
        module_width = estimate_module_width_from_total(runs)
        bits = runs_to_bits(runs, module_width)

        if len(bits) < 80:
            return None

        bits = normalize_to_95_bits(bits)

        if not is_valid_ean_structure(bits):
            return None

        result = decode_ean13_bits(bits)

        return result, 0.3  # fallback gyengébb

    except Exception:
        return None


def try_decode_roi(roi):
    gray = to_grayscale(roi)

    binaries = [
        binarize_adaptive(gray),
        binarize_otsu(gray),
    ]

    results = []
    band_height = 3

    for binary in binaries:
        height = binary.shape[0]

        for y in get_scan_y_positions(height, count=80):
            y1 = max(0, y - band_height // 2)
            y2 = min(height, y + band_height // 2 + 1)

            band = binary[y1:y2, :]

            scanline = band.mean(axis=0)

            res = try_decode_scanline(scanline)

            if res:
                results.append(res)

    return results


# Kép forgatása az alábbi fokokban: 0, 90, 180, 270
def generate_image_variants(image):
    return [
        image,
        cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE),
        cv2.rotate(image, cv2.ROTATE_180),
        cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE),
    ]


def read_ean13_from_image(path: str) -> str:
    image = load_image(path)

    score_map = defaultdict(float)

    for variant in generate_image_variants(image):
        rois = detect_barcode_candidates(variant, max_candidates=15)

        for roi in rois:
            results = try_decode_roi(roi)

            for value, confidence in results:
                score_map[value] += confidence

    if not score_map:
        raise ValueError("Nem sikerült olvasni")

    best = max(score_map.items(), key=lambda x: x[1])

    return best[0]
