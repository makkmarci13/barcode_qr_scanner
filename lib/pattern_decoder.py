from lib.decoder import validate_checksum
from lib.ean13_patterns import FIRST_DIGIT_PARITY


L_RUNS = {
    "0": [3, 2, 1, 1],
    "1": [2, 2, 2, 1],
    "2": [2, 1, 2, 2],
    "3": [1, 4, 1, 1],
    "4": [1, 1, 3, 2],
    "5": [1, 2, 3, 1],
    "6": [1, 1, 1, 4],
    "7": [1, 3, 1, 2],
    "8": [1, 2, 1, 3],
    "9": [3, 1, 1, 2],
}

G_RUNS = {
    "0": [1, 1, 2, 3],
    "1": [1, 2, 2, 2],
    "2": [2, 2, 1, 2],
    "3": [1, 1, 4, 1],
    "4": [2, 3, 1, 1],
    "5": [1, 3, 2, 1],
    "6": [4, 1, 1, 1],
    "7": [2, 1, 3, 1],
    "8": [3, 1, 2, 1],
    "9": [2, 1, 1, 3],
}

R_RUNS = L_RUNS


def normalize(values):
    total = sum(values)

    if total == 0:
        return values

    return [v / total for v in values]


def distance(a, b):
    a_norm = normalize(a)
    b_norm = normalize(b)

    return sum((x - y) ** 2 for x, y in zip(a_norm, b_norm))


def match_digit(runs, side):
    if len(runs) != 4:
        raise ValueError("Egy számjegyhez pontosan 4 run kell.")

    if side == "left":
        tables = [
            ("L", L_RUNS),
            ("G", G_RUNS),
        ]
    elif side == "right":
        tables = [
            ("R", R_RUNS),
        ]
    else:
        raise ValueError("side csak 'left' vagy 'right' lehet.")

    best_digit = None
    best_parity = None
    best_score = float("inf")

    for parity, table in tables:
        for digit, pattern in table.items():
            score = distance(runs, pattern)

            if score < best_score:
                best_score = score
                best_digit = digit
                best_parity = parity

    return best_digit, best_parity, best_score


def find_start_guard(runs):
    """
    Start guard: fekete-fehér-fekete, kb. 1:1:1.
    Mivel trim után általában feketével indulunk, legtöbbször index 0.
    De zaj miatt keresünk is.
    """

    best_index = None
    best_score = float("inf")

    for i in range(0, min(10, len(runs) - 3)):
        colors = [runs[i][0], runs[i + 1][0], runs[i + 2][0]]
        lengths = [runs[i][1], runs[i + 1][1], runs[i + 2][1]]

        if colors != [1, 0, 1]:
            continue

        score = distance(lengths, [1, 1, 1])

        if score < best_score:
            best_score = score
            best_index = i

    if best_index is None:
        raise ValueError("Start guard nem található.")

    return best_index


def decode_ean13_from_runs(colored_runs):
    """
    colored_runs formátum:
    [
        (1, hossz),  # fekete
        (0, hossz),  # fehér
        ...
    ]
    """

    if len(colored_runs) < 50:
        raise ValueError("Túl kevés run EAN-13 dekódoláshoz.")

    start = find_start_guard(colored_runs)

    # start guard = 3 run
    i = start + 3

    left_digits = ""
    parity_pattern = ""
    total_score = 0.0

    # bal oldal: 6 számjegy × 4 run
    for _ in range(6):
        digit_runs = [length for _, length in colored_runs[i:i + 4]]

        digit, parity, score = match_digit(digit_runs, side="left")

        left_digits += digit
        parity_pattern += parity
        total_score += score

        i += 4

    # middle guard: 5 run, kb. 1:1:1:1:1
    middle_colors = [color for color, _ in colored_runs[i:i + 5]]
    middle_lengths = [length for _, length in colored_runs[i:i + 5]]

    if middle_colors != [0, 1, 0, 1, 0]:
        raise ValueError("Middle guard színsorrend hibás.")

    middle_score = distance(middle_lengths, [1, 1, 1, 1, 1])

    if middle_score > 0.15:
        raise ValueError("Middle guard arány hibás.")

    i += 5

    right_digits = ""

    # jobb oldal: 6 számjegy × 4 run
    for _ in range(6):
        digit_runs = [length for _, length in colored_runs[i:i + 4]]

        digit, parity, score = match_digit(digit_runs, side="right")

        right_digits += digit
        total_score += score

        i += 4

    # end guard: 3 run, fekete-fehér-fekete
    end_colors = [color for color, _ in colored_runs[i:i + 3]]
    end_lengths = [length for _, length in colored_runs[i:i + 3]]

    if end_colors != [1, 0, 1]:
        raise ValueError("End guard színsorrend hibás.")

    end_score = distance(end_lengths, [1, 1, 1])

    if end_score > 0.15:
        raise ValueError("End guard arány hibás.")

    if parity_pattern not in FIRST_DIGIT_PARITY:
        raise ValueError(f"Érvénytelen parity pattern: {parity_pattern}")

    first_digit = FIRST_DIGIT_PARITY[parity_pattern]

    ean13 = first_digit + left_digits + right_digits

    if not validate_checksum(ean13):
        raise ValueError(f"Hibás checksum: {ean13}")

    return ean13, total_score