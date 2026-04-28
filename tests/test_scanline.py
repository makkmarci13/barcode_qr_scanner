from lib.scanline import scanline_to_runs, trim_white_runs, runs_to_bits


def test_scanline_to_runs():
    scanline = [
        255, 255, 255,
        0, 0,
        255,
        0, 0, 0
    ]

    runs = scanline_to_runs(scanline)

    assert runs == [
        (0, 3),
        (1, 2),
        (0, 1),
        (1, 3),
    ]


def test_trim_white_runs():
    runs = [
        (0, 5),
        (1, 2),
        (0, 1),
        (1, 3),
        (0, 6),
    ]

    assert trim_white_runs(runs) == [
        (1, 2),
        (0, 1),
        (1, 3),
    ]


def test_runs_to_bits():
    runs = [
        (1, 2),
        (0, 2),
        (1, 4),
    ]

    bits = runs_to_bits(runs, module_width=2)

    assert bits == "1011"
