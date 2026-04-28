from lib.image_processing import load_image, to_grayscale, binarize
from lib.scanline import scanline_to_runs, trim_white_runs, runs_to_bits
from lib.decoder import decode_ean13_bits
from collections import Counter


def estimate_module_width_from_total(runs):
    total_width = sum(length for _, length in runs)

    return total_width / 95


def normalize_to_95_bits(bits: str) -> str:
    """
    A scanline-ból kapott bitstring nem mindig pontosan 95 hosszú, emiatt át kell méretezni mindenképpen 95 modul hosszúságúra.
    """

    if len(bits) < 80:
        raise ValueError("Túl rövid bitstring, valószínűleg nem EAN-13.")

    result = ""

    for i in range(95):
        index = int(i * len(bits) / 95)
        result += bits[index]

    return result


def try_decode_scanline(scanline, debug=False) -> str:
    runs = scanline_to_runs(scanline)
    runs = trim_white_runs(runs)

    module_width = estimate_module_width_from_total(runs)
    bits = runs_to_bits(runs, module_width)

    if len(bits) != 95:
        bits = normalize_to_95_bits(bits)

    if debug:
        print("runs:", runs)
        print("module_width:", module_width)
        print("bits length:", len(bits))
        print("bits:", bits)
        print("start:", bits[0:3])
        print("middle:", bits[45:50])
        print("end:", bits[92:95])

    return decode_ean13_bits(bits)


def get_scan_y_positions(height, count=30):
    start = int(height * 0.10)
    end = int(height * 0.65)

    if count <= 1:
        return [height // 2]

    step = (end - start) / (count - 1)

    return [int(start + i * step) for i in range(count)]


def read_ean13_from_image(path: str) -> str:
    image = load_image(path)
    gray = to_grayscale(image)
    binary = binarize(gray)

    height = binary.shape[0]
    scan_y_positions = get_scan_y_positions(height, count=40)

    results = []
    errors = []

    for y in scan_y_positions:
        scanline = binary[y, :]

        try:
            result = try_decode_scanline(scanline, debug=False)
            results.append(result)
        except Exception as error:
            errors.append(str(error))

    if results:
        return Counter(results).most_common(1)[0][0]

    raise ValueError(
        "Nem sikerült EAN-13 vonalkódot olvasni. Hibák: "
        + " | ".join(errors[:5])
    )
