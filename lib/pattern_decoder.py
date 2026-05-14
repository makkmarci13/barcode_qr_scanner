from dataclasses import dataclass
from typing import Iterable

from lib.decoder import calculate_checksum, validate_checksum
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

# A jobb oldali R minták run-hossz arányban ugyanazok, mint az L minták,
# csak a színek fordítottak. Mivel itt külön kezeljük a színsorrendet, a hossz-minta elég.
R_RUNS = L_RUNS


@dataclass(frozen=True)
class DigitMatch:
    digit: str
    parity: str
    score: float
    margin: float


def normalize(values: Iterable[float]) -> list[float]:
    values = list(values)
    total = sum(values)

    if total == 0:
        return values

    return [v / total for v in values]


def distance(a, b):
    a_norm = normalize(a)
    b_norm = normalize(b)

    return sum((x - y) ** 2 for x, y in zip(a_norm, b_norm))


def _format_runs(runs) -> str:
    return ",".join(str(int(v)) for v in runs)


def match_digit(runs, side, max_score=0.030, min_margin=0.001):
    """
    Visszaadja a legjobb számjegyet, de csak akkor, ha a minta elég közel van
    egy ismert EAN-13 run mintához. A margin azt mutatja, mennyivel jobb a
    legjobb találat a második legjobbnál; ez segít kiszűrni az ambivalens mintákat.
    """
    if len(runs) != 4:
        raise ValueError(f"Egy számjegyhez pontosan 4 run kell, kapott: {len(runs)}.")

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

    matches = []

    for parity, table in tables:
        for digit, pattern in table.items():
            score = distance(runs, pattern)
            matches.append(DigitMatch(digit=digit, parity=parity, score=score, margin=0.0))

    matches.sort(key=lambda item: item.score)
    best = matches[0]
    second = matches[1]
    margin = second.score - best.score
    best = DigitMatch(best.digit, best.parity, best.score, margin)

    if best.score > max_score:
        raise ValueError(
            f"Gyenge számjegy-minta ({side}): runs=[{_format_runs(runs)}], "
            f"legjobb={best.digit}/{best.parity}, score={best.score:.4f}, "
            f"engedélyezett max={max_score:.4f}."
        )

    # A margin túl szigorúra állítása sok valódi, zajos képet kidobna, ezért csak
    # nagyon rossz/ambivalens esetben blokkolunk.
    if best.margin < min_margin and best.score > max_score * 0.55:
        raise ValueError(
            f"Bizonytalan számjegy-minta ({side}): runs=[{_format_runs(runs)}], "
            f"legjobb={best.digit}/{best.parity}, score={best.score:.4f}, "
            f"margin={best.margin:.4f}."
        )

    return best.digit, best.parity, best.score


def find_start_guard(runs, max_search=14, max_score=0.060):
    """
    Start guard: fekete-fehér-fekete, kb. 1:1:1.
    Trim után általában index 0, de zaj / quiet zone maradvány miatt keresünk.
    """

    best_index = None
    best_score = float("inf")

    for i in range(0, min(max_search, len(runs) - 3)):
        colors = [runs[i][0], runs[i + 1][0], runs[i + 2][0]]
        lengths = [runs[i][1], runs[i + 1][1], runs[i + 2][1]]

        if colors != [1, 0, 1]:
            continue

        score = distance(lengths, [1, 1, 1])

        if score < best_score:
            best_score = score
            best_index = i

    if best_index is None:
        raise ValueError("Start guard nem található: nincs fekete-fehér-fekete run-sorrend az elején.")

    if best_score > max_score:
        raise ValueError(
            f"Start guard arány hibás: score={best_score:.4f}, engedélyezett max={max_score:.4f}."
        )

    return best_index


def _require_available_runs(colored_runs, index, needed, label):
    available = len(colored_runs) - index
    if available < needed:
        raise ValueError(f"Kevés run a(z) {label} részhez: kellene {needed}, elérhető {available}.")


def decode_ean13_from_runs(colored_runs):
    """
    colored_runs formátum:
    [
        (1, hossz),  # fekete
        (0, hossz),  # fehér
        ...
    ]

    Visszatérés: (ean13, total_score)
    """

    if len(colored_runs) < 50:
        raise ValueError(f"Túl kevés run EAN-13 dekódoláshoz: {len(colored_runs)} < 50.")

    start = find_start_guard(colored_runs)

    # start guard = 3 run
    i = start + 3

    left_digits = ""
    parity_pattern = ""
    total_score = 0.0

    # bal oldal: 6 számjegy × 4 run
    for position in range(6):
        _require_available_runs(colored_runs, i, 4, f"bal {position + 1}. számjegy")
        digit_runs = [length for _, length in colored_runs[i:i + 4]]

        digit, parity, score = match_digit(digit_runs, side="left")

        left_digits += digit
        parity_pattern += parity
        total_score += score

        i += 4

    # middle guard: 5 run, kb. 1:1:1:1:1
    _require_available_runs(colored_runs, i, 5, "middle guard")
    middle_colors = [color for color, _ in colored_runs[i:i + 5]]
    middle_lengths = [length for _, length in colored_runs[i:i + 5]]

    if middle_colors != [0, 1, 0, 1, 0]:
        raise ValueError(f"Middle guard színsorrend hibás: {middle_colors}, várt: [0, 1, 0, 1, 0].")

    middle_score = distance(middle_lengths, [1, 1, 1, 1, 1])

    if middle_score > 0.080:
        raise ValueError(f"Middle guard arány hibás: score={middle_score:.4f}, runs=[{_format_runs(middle_lengths)}].")

    total_score += middle_score
    i += 5

    right_digits = ""

    # jobb oldal: 6 számjegy × 4 run
    for position in range(6):
        _require_available_runs(colored_runs, i, 4, f"jobb {position + 1}. számjegy")
        digit_runs = [length for _, length in colored_runs[i:i + 4]]

        digit, parity, score = match_digit(digit_runs, side="right")

        right_digits += digit
        total_score += score

        i += 4

    # end guard: 3 run, fekete-fehér-fekete
    _require_available_runs(colored_runs, i, 3, "end guard")
    end_colors = [color for color, _ in colored_runs[i:i + 3]]
    end_lengths = [length for _, length in colored_runs[i:i + 3]]

    if end_colors != [1, 0, 1]:
        raise ValueError(f"End guard színsorrend hibás: {end_colors}, várt: [1, 0, 1].")

    end_score = distance(end_lengths, [1, 1, 1])

    if end_score > 0.080:
        raise ValueError(f"End guard arány hibás: score={end_score:.4f}, runs=[{_format_runs(end_lengths)}].")

    total_score += end_score

    if parity_pattern not in FIRST_DIGIT_PARITY:
        raise ValueError(
            f"Érvénytelen parity pattern: {parity_pattern}. "
            f"A bal oldali 6 számjegy L/G mintája alapján nem határozható meg az első számjegy."
        )

    first_digit = FIRST_DIGIT_PARITY[parity_pattern]

    ean13 = first_digit + left_digits + right_digits

    expected_checksum = calculate_checksum(ean13[:12])
    if not validate_checksum(ean13):
        raise ValueError(
            f"Hibás checksum: olvasott={ean13}, számított utolsó számjegy={expected_checksum}, "
            f"olvasott utolsó számjegy={ean13[-1]}."
        )

    return ean13, total_score
