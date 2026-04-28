import cv2
import numpy as np


def detect_barcode_candidates(image, max_candidates=5):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    candidates = []

    kernel_sizes = [
        (21, 7),
        (31, 9),
        (45, 11),
    ]

    for kernel_size in kernel_sizes:
        grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=-1)
        grad_x = cv2.convertScaleAbs(grad_x)

        blurred = cv2.GaussianBlur(grad_x, (9, 9), 0)

        _, thresh = cv2.threshold(
            blurred,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, kernel_size)
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        closed = cv2.erode(closed, None, iterations=1)
        closed = cv2.dilate(closed, None, iterations=2)

        contours, _ = cv2.findContours(
            closed,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        for contour in contours:
            rect = cv2.minAreaRect(contour)
            (cx, cy), (w, h), angle = rect

            if w == 0 or h == 0:
                continue

            long_side = max(w, h)
            short_side = min(w, h)

            if long_side < 80 or short_side < 15:
                continue

            aspect_ratio = long_side / short_side

            if aspect_ratio < 1.8:
                continue

            area = long_side * short_side

            candidates.append({
                "rect": rect,
                "score": area * aspect_ratio,
            })

    candidates = sorted(candidates, key=lambda c: c["score"], reverse=True)

    rois = []

    for candidate in candidates[:max_candidates]:
        roi = crop_rotated_rect(image, candidate["rect"], padding=0.20)
        rois.append(roi)

    return rois


def crop_rotated_rect(image, rect, padding=0.15):
    (cx, cy), (w, h), angle = rect

    w = w * (1 + padding)
    h = h * (1 + padding)

    rect = ((cx, cy), (w, h), angle)

    box = cv2.boxPoints(rect)
    box = np.intp(box)

    width = int(max(w, h))
    height = int(min(w, h))

    src_pts = box.astype("float32")

    # pontok sorrendezése
    src_pts = order_points(src_pts)

    dst_pts = np.array([
        [0, 0],
        [width - 1, 0],
        [width - 1, height - 1],
        [0, height - 1],
    ], dtype="float32")

    matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
    warped = cv2.warpPerspective(image, matrix, (width, height))

    if warped.shape[0] > warped.shape[1]:
        warped = cv2.rotate(warped, cv2.ROTATE_90_CLOCKWISE)

    return warped


def order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")

    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]

    return rect
