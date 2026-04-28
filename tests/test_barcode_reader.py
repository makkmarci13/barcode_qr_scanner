from lib.barcode_reader import normalize_to_95_bits


def test_normalize_to_95_bits_keeps_95_length():
    bits = "101" * 40

    normalized = normalize_to_95_bits(bits)

    assert len(normalized) == 95
