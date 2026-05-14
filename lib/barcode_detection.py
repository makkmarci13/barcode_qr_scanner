import cv2
import numpy as np


def detect_barcode_candidates(image, max_candidates=5):
    # Szürkeárnyalatossá transzformálás
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    candidates = []

    kernel_sizes = [
        (21, 7),
        (31, 9),
        (45, 11),
    ]

    gray = np.asarray(gray, dtype=np.uint8)
    erode_dilate_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))

    for kernel_size in kernel_sizes:
        # Éldetektálás sobel filterrel
        grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=-1)

        # Mivel a sobel értéke lehet negatív is, ezért abszolútértéket kell venni
        grad_x = cv2.convertScaleAbs(grad_x)

        # Zaj simítása
        blurred = cv2.GaussianBlur(grad_x, (9, 9), 0)

        # Fekete, fehér képpé alakítás
        _, thresh = cv2.threshold(
            blurred,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

        # Kernel készítése
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, kernel_size)

        # Közeli fehér részek összekötése, sok különálló fehér csíkból egy blokk lesz
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        # Fehér területekből kicsi visszavevés
        closed = cv2.erode(closed, erode_dilate_kernel, iterations=1)

        # Fehér területek tágítása
        closed = cv2.dilate(closed, erode_dilate_kernel, iterations=2)

        # Kontúrok keresése
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

    # Fallback: a klasszikus Sobel+minAreaRect detektor néha nem találja meg a
    # függőlegesen álló / címkébe ágyazott vonalkódot. Ilyenkor sötét, hosszú
    # vonalakból próbálunk egy közvetlen, tengelyhez igazított kivágást készíteni.
    for roi in detect_dark_vertical_barcode_candidates(image, max_candidates=max_candidates):
        rois.append(roi)

    return deduplicate_rois(rois, max_candidates=max_candidates)



def detect_dark_vertical_barcode_candidates(image, max_candidates=5):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Fekete elemek kiemelése. A barcode sávjai általában hosszú, vékony,
    # egymáshoz közeli sötét vonalak; a szöveg kisebb komponensekre esik szét.
    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31,
        15,
    )

    h, w = binary.shape[:2]
    vertical_len = max(18, min(55, h // 25))

    # A betűk nagy részét eltüntetjük, a hosszú barcode-sávok megmaradnak.
    opened = cv2.morphologyEx(
        binary,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, vertical_len)),
    )

    # A közeli barcode-sávokat egy blokká kötjük.
    closed = cv2.morphologyEx(
        opened,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (45, 15)),
    )

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidates = []
    image_area = max(1, h * w)

    for contour in contours:
        x, y, bw, bh = cv2.boundingRect(contour)

        if bw < 35 or bh < 70:
            continue

        area = bw * bh
        if area < image_area * 0.002:
            continue

        # A fallback célzottan a magasabb, keskenyebb barcode-blokkokat keresi.
        # Nem túl szigorú, mert a perspektíva és a csomagolás görbülete torzíthat.
        ratio = max(bw, bh) / max(1, min(bw, bh))
        if ratio < 1.5:
            continue

        score = area * ratio
        candidates.append((score, x, y, bw, bh))

    candidates.sort(reverse=True)

    rois = []
    for _, x, y, bw, bh in candidates[:max_candidates]:
        pad_x = int(bw * 0.90)
        pad_y = int(bh * 0.18)

        x1 = max(0, x - pad_x)
        y1 = max(0, y - pad_y)
        x2 = min(w, x + bw + pad_x)
        y2 = min(h, y + bh + pad_y)

        roi = image[y1:y2, x1:x2]
        if roi.size > 0:
            rois.append(roi)

    return rois


def deduplicate_rois(rois, max_candidates=20):
    unique = []
    seen = set()

    for roi in rois:
        if roi is None or roi.size == 0:
            continue

        shape_key = roi.shape[:2]
        # Durva deduplikáció: ugyanabból a kontúrból sok kernelméret mellett
        # majdnem azonos ROI jöhetne létre.
        key = (round(shape_key[0] / 10), round(shape_key[1] / 10))
        if key in seen:
            continue

        seen.add(key)
        unique.append(roi)

        if len(unique) >= max_candidates:
            break

    return unique

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
