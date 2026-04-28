def extract_middle_scanline(binary_image):
    height = binary_image.shape[0]
    middle_y = height // 2

    return binary_image[middle_y, :]


def scanline_to_runs(scanline):
    runs = []

    current_color = 1 if scanline[0] < 128 else 0
    current_length = 1

    for pixel in scanline[1:]:
        color = 1 if pixel < 128 else 0

        if color == current_color:
            current_length += 1
        else:
            runs.append((current_color, current_length))
            current_color = color
            current_length = 1

    runs.append((current_color, current_length))

    return runs


def trim_white_runs(runs):
    while runs and runs[0][0] == 0:
        runs.pop(0)

    while runs and runs[-1][0] == 0:
        runs.pop()

    return runs


def estimate_module_width(runs):
    lengths = [length for _, length in runs]

    if not lengths:
        raise ValueError("Nincs run-length adat.")

    return min(lengths)


def runs_to_bits(runs, module_width):
    bits = ""

    for color, length in runs:
        count = round(length / module_width)
        bits += str(color) * count

    return bits
