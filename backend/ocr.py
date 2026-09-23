import cv2
import numpy as np
import pytesseract
from pytesseract import Output


# ============================================================
# SETTINGS
# ============================================================

FRONT_TARGET_WIDTH = 1600
BACK_TARGET_WIDTH = 1800

MIN_WORD_CONFIDENCE = 30


# ============================================================
# IMAGE RESIZING
# ============================================================

def resize_image(
    image,
    target_width
):
    """
    Enlarge smaller images while avoiding
    unnecessary resizing of already-large images.
    """

    height, width = image.shape[:2]

    if width >= target_width:
        return image

    scale = target_width / width

    return cv2.resize(
        image,
        None,
        fx=scale,
        fy=scale,
        interpolation=cv2.INTER_CUBIC
    )


# ============================================================
# CONSERVATIVE DESKEW
# ============================================================

def deskew_image(image):
    """
    Try to straighten a mildly tilted label.

    This is intentionally conservative.
    Large detected angles are ignored because
    bottle shapes and graphics can confuse
    automatic angle detection.
    """

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    blurred = cv2.GaussianBlur(
        gray,
        (5, 5),
        0
    )

    _, threshold = cv2.threshold(
        blurred,
        0,
        255,
        cv2.THRESH_BINARY_INV
        + cv2.THRESH_OTSU
    )

    coordinates = np.column_stack(
        np.where(
            threshold > 0
        )
    )

    if len(coordinates) < 100:
        return image

    angle = cv2.minAreaRect(
        coordinates
    )[-1]

    if angle < -45:
        angle = 90 + angle

    if abs(angle) > 7:
        return image

    if abs(angle) < 0.5:
        return image

    height, width = image.shape[:2]

    center = (
        width // 2,
        height // 2
    )

    rotation_matrix = cv2.getRotationMatrix2D(
        center,
        angle,
        1.0
    )

    rotated = cv2.warpAffine(
        image,
        rotation_matrix,
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE
    )

    return rotated


# ============================================================
# IMAGE PREPROCESSING
# ============================================================

def make_gray(image):
    return cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )


def enhance_gray(gray):
    """
    Improve local contrast and apply mild
    sharpening without aggressively destroying
    stylized label lettering.
    """

    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8)
    )

    contrast = clahe.apply(
        gray
    )

    blurred = cv2.GaussianBlur(
        contrast,
        (0, 0),
        1.0
    )

    sharpened = cv2.addWeighted(
        contrast,
        1.5,
        blurred,
        -0.5,
        0
    )

    return sharpened


def make_adaptive_threshold(gray):
    """
    Used mainly for small dense back-label text.
    """

    return cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11
    )


# ============================================================
# TARGETED REGIONS
# ============================================================

def crop_region(
    image,
    top_ratio,
    bottom_ratio,
    left_ratio,
    right_ratio
):
    height, width = image.shape[:2]

    top = int(
        height * top_ratio
    )

    bottom = int(
        height * bottom_ratio
    )

    left = int(
        width * left_ratio
    )

    right = int(
        width * right_ratio
    )

    return image[
        top:bottom,
        left:right
    ]


def get_front_brand_region(image):
    """
    Central front-label region where brand text
    is often prominent.
    """

    return crop_region(
        image,
        0.15,
        0.75,
        0.08,
        0.92
    )


def get_front_lower_region(image):
    """
    Lower part of front label where class/type,
    ABV or volume may sometimes appear.
    """

    return crop_region(
        image,
        0.45,
        0.95,
        0.08,
        0.92
    )


def get_back_text_region(image):
    """
    Focus on the central/lower part of the back
    label where regulatory and producer text
    is commonly located.
    """

    return crop_region(
        image,
        0.15,
        0.95,
        0.05,
        0.95
    )


# ============================================================
# OCR WORD QUALITY
# ============================================================

def is_useful_word(word):
    cleaned = "".join(
        character
        for character in word
        if character.isalnum()
    )

    if len(cleaned) < 2:
        return False

    letters = sum(
        character.isalpha()
        for character in cleaned
    )

    digits = sum(
        character.isdigit()
        for character in cleaned
    )

    return (
        letters >= 2
        or digits >= 2
    )


# ============================================================
# SINGLE TESSERACT PASS
# ============================================================

def run_ocr(
    image,
    psm
):
    config = (
        f"--oem 3 "
        f"--psm {psm} "
        "-c preserve_interword_spaces=1"
    )

    data = pytesseract.image_to_data(
        image,
        config=config,
        output_type=Output.DICT
    )

    words = []
    confidences = []

    for index, raw_text in enumerate(
        data["text"]
    ):
        text = raw_text.strip()

        if not text:
            continue

        try:
            confidence = float(
                data["conf"][index]
            )

        except (
            ValueError,
            TypeError
        ):
            confidence = -1

        if (
            confidence
            < MIN_WORD_CONFIDENCE
        ):
            continue

        words.append(
            text
        )

        confidences.append(
            confidence
        )

    if not words:
        return {
            "text": "",
            "confidence": 0,
            "word_count": 0,
            "useful_ratio": 0,
            "score": 0,
        }

    text = " ".join(
        words
    ).strip()

    average_confidence = (
        sum(confidences)
        / len(confidences)
    )

    useful_words = [
        word
        for word in words
        if is_useful_word(
            word
        )
    ]

    useful_ratio = (
        len(useful_words)
        / len(words)
    )

    score = (
        average_confidence
        + min(
            len(useful_words),
            30
        ) * 0.5
        + useful_ratio * 20
    )

    if len(text) > 900:
        score -= 15

    if useful_ratio < 0.30:
        score -= 15

    return {
        "text":
            text,

        "confidence":
            round(
                average_confidence,
                1
            ),

        "word_count":
            len(
                useful_words
            ),

        "useful_ratio":
            useful_ratio,

        "score":
            score,
    }


# ============================================================
# FRONT LABEL OCR
# ============================================================

def run_front_ocr(image):
    """
    Front-label strategy:

    1. Whole image — sparse text
    2. Brand region — sparse / prominent text
    3. Lower region — class, ABV, net contents

    Only three OCR passes are used.
    """

    resized = resize_image(
        image,
        FRONT_TARGET_WIDTH
    )

    resized = deskew_image(
        resized
    )

    gray = make_gray(
        resized
    )

    enhanced = enhance_gray(
        gray
    )

    full_result = run_ocr(
        enhanced,
        psm=11
    )

    brand_region = get_front_brand_region(
        resized
    )

    brand_gray = make_gray(
        brand_region
    )

    brand_enhanced = enhance_gray(
        brand_gray
    )

    brand_result = run_ocr(
        brand_enhanced,
        psm=11
    )

    lower_region = get_front_lower_region(
        resized
    )

    lower_gray = make_gray(
        lower_region
    )

    lower_enhanced = enhance_gray(
        lower_gray
    )

    lower_result = run_ocr(
        lower_enhanced,
        psm=6
    )

    return [
        full_result,
        brand_result,
        lower_result,
    ]


# ============================================================
# BACK LABEL OCR
# ============================================================

def run_back_ocr(image):
    """
    Back-label strategy:

    1. Whole image — block text
    2. Main text region — dense text
    3. Thresholded main region — small print

    Only three OCR passes are used.
    """

    resized = resize_image(
        image,
        BACK_TARGET_WIDTH
    )

    resized = deskew_image(
        resized
    )

    gray = make_gray(
        resized
    )

    enhanced = enhance_gray(
        gray
    )

    full_result = run_ocr(
        enhanced,
        psm=6
    )

    text_region = get_back_text_region(
        resized
    )

    region_gray = make_gray(
        text_region
    )

    region_enhanced = enhance_gray(
        region_gray
    )

    region_result = run_ocr(
        region_enhanced,
        psm=6
    )

    region_threshold = make_adaptive_threshold(
        region_enhanced
    )

    threshold_result = run_ocr(
        region_threshold,
        psm=11
    )

    return [
        full_result,
        region_result,
        threshold_result,
    ]


# ============================================================
# TEXT MERGING
# ============================================================

def normalize_token_for_merge(token):
    return "".join(
        character.lower()
        for character in token
        if character.isalnum()
        or character in ".%"
    )


def merge_ocr_results(results):
    """
    Combine useful OCR text from multiple passes.

    This avoids losing a word such as Heineken
    because another OCR pass happened to receive
    the highest overall score.
    """

    valid_results = [
        result
        for result in results
        if result["text"]
    ]

    if not valid_results:
        return "", 0

    valid_results.sort(
        key=lambda item:
            item["score"],
        reverse=True
    )

    seen_tokens = set()
    merged_tokens = []

    for result in valid_results:

        tokens = result[
            "text"
        ].split()

        for token in tokens:

            normalized = normalize_token_for_merge(
                token
            )

            if not normalized:
                continue

            if len(normalized) < 2:
                continue

            if normalized in seen_tokens:
                continue

            seen_tokens.add(
                normalized
            )

            merged_tokens.append(
                token
            )

    merged_text = " ".join(
        merged_tokens
    )

    best_confidences = [
        result["confidence"]
        for result in valid_results[:2]
    ]

    confidence = round(
        sum(best_confidences)
        / len(best_confidences),
        1
    )

    return (
        merged_text,
        confidence
    )


# ============================================================
# OPTIONAL CENTER CROP
# ============================================================

def apply_optional_center_crop(
    image
):
    height, width = image.shape[:2]

    return image[
        int(height * 0.08):
        int(height * 0.92),

        int(width * 0.08):
        int(width * 0.92)
    ]


# ============================================================
# MAIN OCR FUNCTION
# ============================================================

def extract_text_from_image(
    image_bytes: bytes,
    use_center_crop: bool = False,
    label_side: str = "front"
):
    """
        Main OCR entry point.

        main.py calls this with label_side set to
        "front" or "back".
    """

    image_array = np.frombuffer(
        image_bytes,
        dtype=np.uint8
    )

    image = cv2.imdecode(
        image_array,
        cv2.IMREAD_COLOR
    )

    if image is None:
        raise ValueError(
            "Unable to read uploaded image."
        )

    if use_center_crop:
        image = apply_optional_center_crop(
            image
        )

    if (
        label_side.lower()
        == "back"
    ):
        results = run_back_ocr(
            image
        )

    else:
        results = run_front_ocr(
            image
        )

    return merge_ocr_results(
        results
    )