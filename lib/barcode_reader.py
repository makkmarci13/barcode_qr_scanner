import cv2
from collections import Counter

from lib.image_processing import load_image, to_grayscale, binarize
from lib.barcode_detection import detect_barcode_candidates
from lib.scanline import scanline_to_runs, trim_white_runs, runs_to_bits
from lib.decoder import decode_ean13_bits


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
    start = int(height * 0.15)
    end = int(height * 0.60)

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


def try_decode_scanline(scanline) -> str:
    runs = scanline_to_runs(scanline)
    runs = trim_white_runs(runs)

    module_width = estimate_module_width_from_total(runs)
    bits = runs_to_bits(runs, module_width)

    if len(bits) < 80:
        raise ValueError("Túl rövid")

    bits = normalize_to_95_bits(bits)

    if not is_valid_ean_structure(bits):
        raise ValueError("Guard pattern fail")

    return decode_ean13_bits(bits)


def try_decode_roi(roi) -> list[str]:
    gray = to_grayscale(roi)
    binary = binarize(gray)

    height = binary.shape[0]
    results = []

    for y in get_scan_y_positions(height, count=40):
        scanline = binary[y, :]

        try:
            result = try_decode_scanline(scanline)
            results.append(result)
        except Exception:
            pass

    return results


def generate_image_variants(image):
    return [
        image,
        cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE),
        cv2.rotate(image, cv2.ROTATE_180),
        cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE),
    ]


def read_ean13_from_image(path: str) -> str:
    image = load_image(path)

    all_results = []

    for variant in generate_image_variants(image):
        rois = detect_barcode_candidates(variant, max_candidates=8)

        for roi in rois:
            all_results.extend(try_decode_roi(roi))

    if not all_results:
        raise ValueError("Nem sikerült olvasni")

    counts = Counter(all_results)
    best, count = counts.most_common(1)[0]

    if count < 3:
        raise ValueError(f"Túl bizonytalan eredmény: {best} ({count}x)")

    return best
