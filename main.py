from __future__ import annotations

import sys
from pathlib import Path

from lib.barcode_reader import read_ean13_from_image

IMAGE_DIR = Path("tests/images")

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def expected_ean_from_filename(path: Path) -> str | None:
    """
    A fájlnév elejéről kiszedi az EAN-13 kódot.
    Pl:
    0310158083511-test.jpg -> 0310158083511
    0310158083511.jpg      -> 0310158083511
    """
    name = path.stem

    digits = ""
    for char in name:
        if char.isdigit():
            digits += char
        else:
            break

    if len(digits) == 13:
        return digits

    return None


def test_single_image(image_path: Path) -> bool:
    expected = expected_ean_from_filename(image_path)

    try:
        result = read_ean13_from_image(str(image_path))

        if expected is None:
            print(f"{YELLOW}[?]{RESET} {image_path.name} -> EAN-13: {result} / nincs elvárt érték a fájlnévben")
            return True

        if result == expected:
            print(f"{GREEN}[OK]{RESET} {image_path.name} -> {result}")
            return True

        print(f"{RED}[ROSSZ]{RESET} {image_path.name} -> olvasott: {result}, elvárt: {expected}")
        return False

    except Exception as error:
        if expected:
            print(f"{RED}[HIBA]{RESET} {image_path.name} -> elvárt: {expected}, hiba: {error}")
        else:
            print(f"{RED}[HIBA]{RESET} {image_path.name} -> {error}")

        return False


def test_folder(folder: Path) -> None:
    image_extensions = {".jpg", ".jpeg", ".png", ".webp"}

    images = sorted(
        path for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in image_extensions
    )

    if not images:
        print(f"{RED}Nincs kép ebben a mappában: {folder}{RESET}")
        sys.exit(1)

    ok_count = 0
    fail_count = 0

    for image_path in images:
        success = test_single_image(image_path)

        if success:
            ok_count += 1
        else:
            fail_count += 1

    print()
    print("Összesítés:")
    print(f"{GREEN}OK: {ok_count}{RESET}")
    print(f"{RED}Hibás: {fail_count}{RESET}")
    print(f"Összesen: {len(images)}")

    if fail_count > 0:
        sys.exit(1)


def main():
    if len(sys.argv) >= 2:
        path = Path(sys.argv[1])

        if path.is_dir():
            test_folder(path)
        elif path.is_file():
            success = test_single_image(path)
            sys.exit(0 if success else 1)
        else:
            print(f"{RED}Nem létezik: {path}{RESET}")
            sys.exit(1)

    else:
        test_folder(IMAGE_DIR)


if __name__ == "__main__":
    main()
