from lib.ean13_patterns import L_CODES, G_CODES, R_CODES, FIRST_DIGIT_PARITY


def calculate_checksum(first_12_digits: str) -> str:
    if len(first_12_digits) != 12:
        raise ValueError("EAN-13 checksum számításhoz pontosan 12 számjegy kell.")

    total = 0

    for i, char in enumerate(first_12_digits):
        digit = int(char)

        if i % 2 == 0:
            total += digit
        else:
            total += digit * 3

    checksum = (10 - (total % 10)) % 10
    return str(checksum)


def validate_checksum(ean13: str) -> bool:
    if len(ean13) != 13 or not ean13.isdigit():
        return False

    return calculate_checksum(ean13[:12]) == ean13[12]


def decode_ean13_bits(bits: str) -> str:
    """
    EAN-13 bitstruktúra:

    start guard: 101
    bal oldal: 6 × 7 bit
    middle guard: 01010
    jobb oldal: 6 × 7 bit
    end guard: 101

    Teljes hossz: 95 bit
    """

    if len(bits) != 95:
        raise ValueError(f"Hibás bit hossz: {len(bits)}. EAN-13 esetén 95 bit kell.")

    if bits[0:3] != "101":
        raise ValueError("Hibás start guard.")

    if bits[45:50] != "01010":
        raise ValueError("Hibás middle guard.")

    if bits[92:95] != "101":
        raise ValueError("Hibás end guard.")

    left_bits = bits[3:45]
    right_bits = bits[50:92]

    left_digits = ""
    parity = ""

    for i in range(6):
        chunk = left_bits[i * 7:(i + 1) * 7]

        if chunk in L_CODES:
            left_digits += L_CODES[chunk]
            parity += "L"
        elif chunk in G_CODES:
            left_digits += G_CODES[chunk]
            parity += "G"
        else:
            raise ValueError(f"Ismeretlen bal oldali minta: {chunk}")

    if parity not in FIRST_DIGIT_PARITY:
        raise ValueError(f"Érvénytelen paritásminta: {parity}")

    first_digit = FIRST_DIGIT_PARITY[parity]

    right_digits = ""

    for i in range(6):
        chunk = right_bits[i * 7:(i + 1) * 7]

        if chunk not in R_CODES:
            raise ValueError(f"Ismeretlen jobb oldali minta: {chunk}")

        right_digits += R_CODES[chunk]

    result = first_digit + left_digits + right_digits

    if not validate_checksum(result):
        raise ValueError(f"Hibás checksum: {result}")

    return result
