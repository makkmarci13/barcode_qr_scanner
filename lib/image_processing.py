import cv2


def load_image(path: str):
    image = cv2.imread(path)

    if image is None:
        raise ValueError(f"Nem sikerült betölteni a képet: {path}")

    return image


def to_grayscale(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def binarize(gray_image):
    return cv2.adaptiveThreshold(
        gray_image,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        10
    )
