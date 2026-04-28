from lib.decoder import decode_ean13_bits, validate_checksum, calculate_checksum
from lib.ean13_patterns import L_CODES, G_CODES, R_CODES

PARITY_BY_FIRST_DIGIT = {
    "0": "LLLLLL",
    "1": "LLGLGG",
    "2": "LLGGLG",
    "3": "LLGGGL",
    "4": "LGLLGG",
    "5": "LGGLLG",
    "6": "LGGGLL",
    "7": "LGLGLG",
    "8": "LGLGGL",
    "9": "LGGLGL",
}


def reverse_dict(d):
    return {v: k for k, v in d.items()}


L_BY_DIGIT = reverse_dict(L_CODES)
G_BY_DIGIT = reverse_dict(G_CODES)
R_BY_DIGIT = reverse_dict(R_CODES)


def encode_ean13_bits(ean13: str) -> str:
    assert len(ean13) == 13
    assert validate_checksum(ean13)

    first_digit = ean13[0]
    left_digits = ean13[1:7]
    right_digits = ean13[7:13]

    parity = PARITY_BY_FIRST_DIGIT[first_digit]

    bits = "101"

    for digit, p in zip(left_digits, parity):
        if p == "L":
            bits += L_BY_DIGIT[digit]
        else:
            bits += G_BY_DIGIT[digit]

    bits += "01010"

    for digit in right_digits:
        bits += R_BY_DIGIT[digit]

    bits += "101"

    return bits


def test_checksum():
    assert calculate_checksum("400638133393") == "1"
    assert validate_checksum("4006381333931") is True


def test_decode_known_ean13():
    ean = "4006381333931"
    bits = encode_ean13_bits(ean)

    assert len(bits) == 95
    assert decode_ean13_bits(bits) == ean
