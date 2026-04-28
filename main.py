import sys

from lib.barcode_reader import read_ean13_from_image


def main():
    if len(sys.argv) < 2:
        print("Használat:")
        print("python main.py path/to/barcode.png")
        sys.exit(1)

    image_path = sys.argv[1]

    try:
        result = read_ean13_from_image(image_path)
        print(f"EAN-13: {result}")
    except Exception as error:
        print(f"Hiba: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
