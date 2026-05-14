from __future__ import annotations

import sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

from lib.barcode_reader import BarcodeReadError, read_ean13_from_image

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


def _format_debug(debug: dict) -> str:
    alternatives = debug.get("alternatives") or []
    alt_text = ""
    if alternatives:
        alt_text = " | alternatívák: " + ", ".join(f"{value}({score:.2f})" for value, score in alternatives[:3])

    return (
        f"score={debug.get('score', 0):.2f}, "
        f"találatok={debug.get('hits', 0)}, "
        f"ROI={debug.get('roi_count', 0)}, "
        f"módszer={debug.get('methods', {})}"
        f"{alt_text}"
    )


def test_single_image(image_path: Path) -> tuple[bool, str]:
    expected = expected_ean_from_filename(image_path)

    try:
        debug = read_ean13_from_image(str(image_path), return_debug=True)
        result = debug["value"]
        debug_text = _format_debug(debug)

        if expected is None:
            return True, f"{YELLOW}[?]{RESET} {image_path.name} -> {result} ({debug_text})"

        if result == expected:
            return True, f"{GREEN}[OK]{RESET} {image_path.name} -> {result} ({debug_text})"

        return False, f"{RED}[ROSSZ]{RESET} {image_path.name} -> {result} != {expected} ({debug_text})"

    except BarcodeReadError as error:
        return False, f"{RED}[HIBA]{RESET} {image_path.name} -> {error}"
    except Exception as error:
        return False, f"{RED}[HIBA]{RESET} {image_path.name} -> váratlan hiba: {error}"


def test_folder(folder: Path) -> None:
    image_extensions = {".jpg", ".jpeg", ".png", ".webp"}

    images = sorted(
        path for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in image_extensions
    )

    if not images:
        print(f"{RED}Nincs kép ebben a mappában: {folder}{RESET}")
        sys.exit(1)

    total = len(images)
    done = 0

    ok_count = 0
    fail_count = 0

    with ProcessPoolExecutor() as executor:
        futures = {executor.submit(test_single_image, path): path for path in images}

        for future in as_completed(futures):
            done += 1

            success, message = future.result()
            print(f"[{done}/{total}] {message}")

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
            success, message = test_single_image(path)
            print(message)
            sys.exit(0 if success else 1)
        else:
            print(f"{RED}Nem létezik: {path}{RESET}")
            sys.exit(1)

    else:
        test_folder(IMAGE_DIR)


if __name__ == "__main__":
    main()
