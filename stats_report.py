from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from lib.barcode_reader import BarcodeReadError, read_ean13_from_image
from main import expected_ean_from_filename

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


@dataclass
class ImageResult:
    filename: str
    expected: str | None
    status: str  # OK, WRONG, ERROR, UNKNOWN_EXPECTED
    result: str | None = None
    error: str | None = None
    error_category: str | None = None
    roi_count: int | None = None
    score: float | None = None
    hits: int | None = None
    methods: dict[str, int] | None = None
    alternatives: list[tuple[str, float]] | None = None


def classify_error(message: str) -> str:
    m = message.lower()

    if "bizonytalan ean-13" in m or "több eltérő kód" in m:
        return "bizonytalan_olvasas"
    if "nem találtam barcode-gyanús" in m or "roi-k száma: 0" in m or "roi-k szama: 0" in m:
        return "nem_talalt_roi"
    if "túl kevés run" in m or "tul keves run" in m or "túl kevés fekete-fehér váltás" in m:
        return "tul_keves_valtas"
    if "checksum" in m:
        return "checksum_hiba"
    if "guard bitstruktúra" in m or "guard bitstruktura" in m:
        return "guard_bitstruktura_hiba"
    if "start guard" in m:
        return "start_guard_hiba"
    if "middle guard" in m:
        return "middle_guard_hiba"
    if "end guard" in m:
        return "end_guard_hiba"
    if "bizonytalan számjegy" in m or "bizonytalan szamjegy" in m:
        return "bizonytalan_szamjegy_minta"
    if "parity" in m:
        return "parity_hiba"
    if "érvénytelen" in m or "ervenytelen" in m:
        return "ervenytelen_minta"

    return "egyeb_hiba"


def scan_one(path: str) -> ImageResult:
    image_path = Path(path)
    expected = expected_ean_from_filename(image_path)

    try:
        debug: dict[str, Any] = read_ean13_from_image(str(image_path), return_debug=True)
        result = debug.get("value")

        base = ImageResult(
            filename=image_path.name,
            expected=expected,
            status="UNKNOWN_EXPECTED" if expected is None else ("OK" if result == expected else "WRONG"),
            result=result,
            roi_count=debug.get("roi_count"),
            score=float(debug.get("score", 0) or 0),
            hits=int(debug.get("hits", 0) or 0),
            methods=debug.get("methods") or {},
            alternatives=debug.get("alternatives") or [],
        )
        return base

    except BarcodeReadError as exc:
        message = str(exc)
        return ImageResult(
            filename=image_path.name,
            expected=expected,
            status="ERROR",
            error=message,
            error_category=classify_error(message),
        )
    except Exception as exc:
        message = f"Váratlan hiba: {exc}"
        return ImageResult(
            filename=image_path.name,
            expected=expected,
            status="ERROR",
            error=message,
            error_category="varatlan_hiba",
        )


def pct(part: int | float, total: int | float) -> float:
    if not total:
        return 0.0
    return round(float(part) * 100.0 / float(total), 2)


def median(values: list[float]) -> float | None:
    values = [v for v in values if v is not None and not math.isnan(v)]
    if not values:
        return None
    return round(float(statistics.median(values)), 2)


def avg(values: list[float]) -> float | None:
    values = [v for v in values if v is not None and not math.isnan(v)]
    if not values:
        return None
    return round(float(statistics.mean(values)), 2)


def method_family(method: str) -> str:
    # adaptive/run/band5 -> adaptive/run
    parts = method.split("/")
    if len(parts) >= 2:
        return "/".join(parts[:2])
    return method


def build_stats(results: list[ImageResult]) -> dict[str, Any]:
    total = len(results)
    status_counts = Counter(r.status for r in results)
    error_counts = Counter(r.error_category or "-" for r in results if r.status == "ERROR")

    ok = [r for r in results if r.status == "OK"]
    wrong = [r for r in results if r.status == "WRONG"]
    errors = [r for r in results if r.status == "ERROR"]

    method_counts: Counter[str] = Counter()
    method_family_counts: Counter[str] = Counter()
    for r in results:
        if r.status in {"OK", "WRONG", "UNKNOWN_EXPECTED"} and r.methods:
            for method, count in r.methods.items():
                method_counts[method] += int(count)
                method_family_counts[method_family(method)] += int(count)

    score_ok = [float(r.score or 0) for r in ok]
    score_wrong = [float(r.score or 0) for r in wrong]
    hits_ok = [float(r.hits or 0) for r in ok]
    hits_wrong = [float(r.hits or 0) for r in wrong]
    roi_success = [float(r.roi_count or 0) for r in results if r.status in {"OK", "WRONG", "UNKNOWN_EXPECTED"}]

    low_conf_wrong = [r for r in wrong if (r.hits or 0) <= 5 or (r.score or 0) <= 5]
    high_conf_wrong = [r for r in wrong if (r.hits or 0) >= 20 or (r.score or 0) >= 20]

    return {
        "total": total,
        "status_counts": dict(status_counts),
        "status_percent": {k: pct(v, total) for k, v in status_counts.items()},
        "error_counts": dict(error_counts),
        "error_percent_of_errors": {k: pct(v, len(errors)) for k, v in error_counts.items()},
        "score_ok_avg": avg(score_ok),
        "score_ok_median": median(score_ok),
        "score_wrong_avg": avg(score_wrong),
        "score_wrong_median": median(score_wrong),
        "hits_ok_avg": avg(hits_ok),
        "hits_ok_median": median(hits_ok),
        "hits_wrong_avg": avg(hits_wrong),
        "hits_wrong_median": median(hits_wrong),
        "roi_success_avg": avg(roi_success),
        "roi_success_median": median(roi_success),
        "method_counts": dict(method_counts.most_common()),
        "method_family_counts": dict(method_family_counts.most_common()),
        "low_conf_wrong": [asdict(r) for r in low_conf_wrong[:30]],
        "high_conf_wrong": [asdict(r) for r in high_conf_wrong[:30]],
        "top_wrong": [asdict(r) for r in sorted(wrong, key=lambda x: float(x.score or 0), reverse=True)[:30]],
        "top_errors": [asdict(r) for r in errors[:30]],
    }


def recommendation_lines(stats: dict[str, Any]) -> list[str]:
    total = stats["total"]
    status = Counter(stats["status_counts"])
    errors = Counter(stats["error_counts"])
    lines: list[str] = []

    wrong = status.get("WRONG", 0)
    error = status.get("ERROR", 0)
    ok = status.get("OK", 0)

    if wrong:
        lines.append(
            "A legfontosabb fejlesztési irány a hamis pozitív találatok csökkentése. "
            "Dokumentációban érdemes kiemelni, hogy a rendszer inkább dobjon bizonytalan hibát, mint rossz EAN-kódot."
        )

    if errors.get("nem_talalt_roi", 0):
        lines.append(
            "Sok esetben már a ROI-detektálás sem talál vonalkód-gyanús területet. "
            "Ezen a barcode-terület keresésének további bővítése segíthet: kisebb/keskenyebb ROI-k, görbült címkék, táblázat melletti vonalkódok, valamint több orientáció kezelése."
        )

    if errors.get("tul_keves_valtas", 0):
        lines.append(
            "Gyakori a túl kevés fekete-fehér váltás. Ez általában azt jelenti, hogy a scanline nem a vonalkódon halad át, "
            "a kivágás túl nagy, a vonalkód túl kicsi, vagy a küszöbölés eltünteti a vékony vonalakat."
        )

    if errors.get("bizonytalan_olvasas", 0):
        lines.append(
            "Több eltérő, checksum-helyes jelölt is előfordul. Itt a konszenzuslogika és a minimális score/találatszám küszöb finomhangolása a kulcs."
        )

    if stats.get("score_wrong_median") is not None and stats.get("score_ok_median") is not None:
        sw = stats["score_wrong_median"] or 0
        so = stats["score_ok_median"] or 0
        if sw and so and sw < so * 0.25:
            lines.append(
                "A rossz találatok medián score-ja jóval alacsonyabb, mint a jó találatoké. "
                "Ez alapján érdemes minimális score- és hits-küszöböt használni."
            )

    if ok and total:
        lines.append(
            f"A jelenlegi sikerarány {pct(ok, total)}%. Ezt a dokumentációban célszerű külön bontani: jó olvasás, rossz olvasás, és biztonságosan elutasított kép."
        )

    if not lines:
        lines.append("A mintában nem látszik domináns hibatípus; több kép vagy részletesebb debug mentés alapján lehet tovább finomítani.")

    return lines


def md_table(rows: list[list[Any]], headers: list[str]) -> str:
    out = []
    out.append("| " + " | ".join(headers) + " |")
    out.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        out.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(out)


def write_markdown(path: Path, results: list[ImageResult], stats: dict[str, Any], source_folder: Path) -> None:
    status_counts = Counter(stats["status_counts"])
    error_counts = Counter(stats["error_counts"])
    total = stats["total"]

    status_rows = []
    for key in ["OK", "WRONG", "ERROR", "UNKNOWN_EXPECTED"]:
        count = status_counts.get(key, 0)
        if count:
            status_rows.append([key, count, f"{pct(count, total)}%"])

    error_rows = []
    err_total = sum(error_counts.values())
    for key, count in error_counts.most_common():
        error_rows.append([key, count, f"{pct(count, err_total)}%"])

    method_rows = []
    for key, count in Counter(stats["method_family_counts"]).most_common(12):
        method_rows.append([key, count])

    wrong_rows = []
    for r in sorted([x for x in results if x.status == "WRONG"], key=lambda x: float(x.score or 0), reverse=True)[:25]:
        wrong_rows.append([r.filename, r.expected, r.result, r.score, r.hits, r.roi_count])

    error_sample_rows = []
    for r in [x for x in results if x.status == "ERROR"][:25]:
        msg = (r.error or "").replace("\n", " ")
        if len(msg) > 180:
            msg = msg[:177] + "..."
        error_sample_rows.append([r.filename, r.error_category, msg])

    content = []
    content.append("# EAN-13 scanner statisztikai riport")
    content.append("")
    content.append(f"Készült: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    content.append(f"Forrásmappa: `{source_folder}`")
    content.append(f"Képek száma: **{total}**")
    content.append("")

    content.append("## 1. Eredményösszesítés")
    content.append("")
    content.append(md_table(status_rows, ["Kategória", "Darab", "Arány"]))
    content.append("")

    content.append("## 2. Minőségi mutatók")
    content.append("")
    content.append(md_table([
        ["Jó találatok átlag score", stats.get("score_ok_avg")],
        ["Jó találatok medián score", stats.get("score_ok_median")],
        ["Rossz találatok átlag score", stats.get("score_wrong_avg")],
        ["Rossz találatok medián score", stats.get("score_wrong_median")],
        ["Jó találatok átlag találatszám", stats.get("hits_ok_avg")],
        ["Rossz találatok átlag találatszám", stats.get("hits_wrong_avg")],
        ["Sikeres dekódolások átlag ROI száma", stats.get("roi_success_avg")],
    ], ["Mutató", "Érték"]))
    content.append("")

    if error_rows:
        content.append("## 3. Hibák gyakorisága")
        content.append("")
        content.append(md_table(error_rows, ["Hibatípus", "Darab", "Arány a hibákon belül"]))
        content.append("")

    if method_rows:
        content.append("## 4. Sikeres és rossz találatok módszer szerinti megoszlása")
        content.append("")
        content.append(md_table(method_rows, ["Módszercsalád", "Találatszám"]))
        content.append("")

    content.append("## 5. Fejlesztési javaslatok")
    content.append("")
    for line in recommendation_lines(stats):
        content.append(f"- {line}")
    content.append("")

    if wrong_rows:
        content.append("## 6. Legfontosabb rossz beolvasások")
        content.append("")
        content.append(md_table(wrong_rows, ["Fájl", "Elvárt", "Olvasott", "Score", "Találatok", "ROI"]))
        content.append("")

    if error_sample_rows:
        content.append("## 7. Példa hibák")
        content.append("")
        content.append(md_table(error_sample_rows, ["Fájl", "Hibatípus", "Rövid hibaüzenet"]))
        content.append("")

    path.write_text("\n".join(content), encoding="utf-8")


def write_csv(path: Path, results: list[ImageResult]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(results[0]).keys()) if results else [])
        if results:
            writer.writeheader()
            for r in results:
                row = asdict(r)
                row["methods"] = json.dumps(row["methods"], ensure_ascii=False)
                row["alternatives"] = json.dumps(row["alternatives"], ensure_ascii=False)
                writer.writerow(row)


def collect_images(folder: Path) -> list[Path]:
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS)


def main() -> int:
    parser = argparse.ArgumentParser(description="EAN-13 scanner statisztikai riport készítése a feldolgozó algoritmus módosítása nélkül.")
    parser.add_argument("folder", type=Path, help="Képmappa, például tests/images")
    parser.add_argument("--out", type=Path, default=Path("scanner_report.md"), help="Markdown riport fájl")
    parser.add_argument("--csv", dest="csv_path", type=Path, default=Path("scanner_results.csv"), help="Részletes CSV eredménylista")
    parser.add_argument("--json", dest="json_path", type=Path, default=Path("scanner_stats.json"), help="Géppel feldolgozható JSON statisztika")
    parser.add_argument("--workers", type=int, default=0, help="Párhuzamos folyamatok száma. 0 = automatikus.")
    args = parser.parse_args()

    folder = args.folder
    if not folder.exists() or not folder.is_dir():
        print(f"Nem létező képmappa: {folder}", file=sys.stderr)
        return 1

    images = collect_images(folder)
    if not images:
        print(f"Nem találtam képeket ebben a mappában: {folder}", file=sys.stderr)
        return 1

    results: list[ImageResult] = []
    workers = args.workers if args.workers and args.workers > 0 else None

    print(f"Képek feldolgozása: {len(images)} db")
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(scan_one, str(path)): path for path in images}
        done = 0
        for future in as_completed(futures):
            done += 1
            result = future.result()
            results.append(result)
            print(f"[{done}/{len(images)}] {result.status}: {result.filename}")

    results.sort(key=lambda r: r.filename)
    stats = build_stats(results)

    write_markdown(args.out, results, stats, folder)
    write_csv(args.csv_path, results)
    args.json_path.write_text(json.dumps({"stats": stats, "results": [asdict(r) for r in results]}, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print(f"Markdown riport: {args.out}")
    print(f"CSV részletek:    {args.csv_path}")
    print(f"JSON stat:        {args.json_path}")
    print()
    print("Gyors összesítés:")
    for key, count in Counter(stats["status_counts"]).most_common():
        print(f"  {key}: {count} ({pct(count, stats['total'])}%)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
