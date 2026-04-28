import cv2


def load_image(path: str):
    image = cv2.imread(path)

    if image is None:
        raise ValueError(f"Nem sikerült betölteni a képet: {path}")

    return image


def to_grayscale(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def binarize_adaptive(gray):
    return cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        10
    )


def binarize_otsu(gray):
    _, binary = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    return binary
