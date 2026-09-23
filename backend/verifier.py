import re
from difflib import SequenceMatcher


# Required government warning text used for wording checks.
GOVERNMENT_WARNING = (
    "GOVERNMENT WARNING: "
    "(1) According to the Surgeon General, women should not drink "
    "alcoholic beverages during pregnancy because of the risk of birth defects. "
    "(2) Consumption of alcoholic beverages impairs your ability to drive a car "
    "or operate machinery, and may cause health problems."
)


# Alcohol classes/types recognized by the prototype.
# Ethiopian traditional drinks are kept here as product types, not brands.
ALCOHOL_TYPES = [
    "beer",
    "lager",
    "ale",
    "stout",
    "porter",
    "malt beverage",
    "ethiopian beer",
    "tella",
    "tej",
    "honey wine",
    "ethiopian honey wine",
    "areki",
    "araq",
    "katikala",
    "wine",
    "red wine",
    "white wine",
    "rose",
    "rosé",
    "sparkling wine",
    "champagne",
    "vodka",
    "whiskey",
    "whisky",
    "bourbon",
    "rum",
    "spiced rum",
    "gin",
    "tequila",
    "brandy",
    "cognac",
    "liqueur",
    "liquor",
    "cider",
    "hard cider",
    "sake",
]


# Ethiopian beer brands used by Scan Only brand detection.
# Brands stay separate from alcohol types so "Beer" can still be a class/type.
ETHIOPIAN_BEER_BRANDS = [
    "Habesha Beer",
    "St. Georgis",
    "Meta Beer",
    "Bedele Beer",
    "Sofi Beer",
    "Waliya Beer",
    "Hakim Stout Beer",
    "Harer Beer",
]


def normalize_text(text):
    """
    Clean text before comparing it.

    Lowercase text, remove most punctuation, and collapse extra spaces so
    small formatting differences do not create a false mismatch.
    """
    if not text:
        return ""

    text = str(text).lower()

    text = text.replace("’", "'")
    text = text.replace("‘", "'")
    text = text.replace("“", '"')
    text = text.replace("”", '"')

    text = re.sub(
        r"[^a-z0-9.%]+",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def normalize_warning_text(text):
    """
    Use a simpler cleanup for government-warning comparisons.
    """
    if not text:
        return ""

    text = str(text).lower()

    text = re.sub(
        r"[^a-z0-9]+",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def similarity(a, b):
    """
    Return a similarity score between 0 and 1.
    """
    return SequenceMatcher(
        None,
        normalize_text(a),
        normalize_text(b)
    ).ratio()


def verify_text_field(expected, ocr_text):
    """
    Compare a regular application field with OCR text.

    An exact normalized match becomes MATCH.
    A close OCR result becomes REVIEW.
    Fuzzy text stays REVIEW to avoid false-positive matches.
    """
    expected_normalized = normalize_text(expected)
    ocr_normalized = normalize_text(ocr_text)

    if not expected_normalized:
        return {
            "status": "REVIEW",
            "detected_value": "No application value provided"
        }

    if not ocr_normalized:
        return {
            "status": "REVIEW",
            "detected_value": "Not confidently detected"
        }

    if expected_normalized in ocr_normalized:
        return {
            "status": "MATCH",
            "detected_value": expected
        }

    words = ocr_normalized.split()
    expected_compact = expected_normalized.replace(" ", "")

    best_candidate = None
    best_score = 0.0

    # First check single OCR words.
    for word in words:
        if len(word) < 2:
            continue

        score = similarity(
            expected_compact,
            word
        )

        if score > best_score:
            best_score = score
            best_candidate = word

    # Then check small groups of neighboring OCR words.
    expected_word_count = max(
        1,
        len(expected_normalized.split())
    )

    window_sizes = sorted(
        set([
            expected_word_count,
            max(1, expected_word_count - 1),
            expected_word_count + 1,
            expected_word_count + 2,
        ])
    )

    for window_size in window_sizes:

        for i in range(
            len(words) - window_size + 1
        ):
            fragment_words = words[
                i:i + window_size
            ]

            candidate_compact = "".join(
                fragment_words
            )

            if len(candidate_compact) < 3:
                continue

            score = SequenceMatcher(
                None,
                expected_compact,
                candidate_compact
            ).ratio()

            if score > best_score:
                best_score = score
                best_candidate = " ".join(
                    fragment_words
                )

    # Fuzzy text can help the reviewer, but it does not count as a match.
    review_threshold = (
        0.72
        if len(expected_compact) <= 7
        else 0.70
    )

    if (
        best_candidate
        and best_score >= review_threshold
    ):
        return {
            "status": "REVIEW",
            "detected_value": best_candidate
        }

    return {
        "status": "REVIEW",
        "detected_value": "Not confidently detected"
    }


def extract_percentages(text):
    """
    Find percentage values and ignore impossible OCR results above 100%.
    """
    if not text:
        return []

    matches = re.findall(
        r"(?<!\d)"
        r"(\d{1,3}(?:\.\d+)?)"
        r"\s*%",
        text
    )

    values = []

    for value in matches:
        try:
            number = float(value)
        except ValueError:
            continue

        if 0 <= number <= 100:
            values.append(number)

    return values


def extract_alcohol_percentages(text):
    """
    Read percentages only when they appear near alcohol-specific wording.

    This helps keep nutrition percentages from being mistaken for ABV.
    """
    if not text:
        return []

    normalized = text.lower()

    patterns = [
        r"alcohol\s+by\s+volume"
        r"[^0-9]{0,25}"
        r"(\d{1,2}(?:\.\d+)?)\s*%",

        r"(\d{1,2}(?:\.\d+)?)\s*%"
        r"[^a-z0-9]{0,10}"
        r"alcohol\s+by\s+volume",

        r"(\d{1,2}(?:\.\d+)?)\s*%"
        r"\s*abv\b",

        r"\babv\b"
        r"[^0-9]{0,15}"
        r"(\d{1,2}(?:\.\d+)?)\s*%",

        r"\balc\.?\s*"
        r"(\d{1,2}(?:\.\d+)?)\s*%"
        r"(?:\s*(?:by\s*)?vol\.?)?",

        r"(\d{1,2}(?:\.\d+)?)\s*%"
        r"\s*alc\.?\s*/?\s*(?:by\s*)?vol\.?",
    ]

    values = []

    for pattern in patterns:
        matches = re.findall(
            pattern,
            normalized,
            flags=re.IGNORECASE
        )

        for value in matches:
            try:
                number = float(value)
            except ValueError:
                continue

            if (
                0 <= number <= 100
                and number not in values
            ):
                values.append(number)

    return values


def verify_alcohol_content(expected, ocr_text):
    """
    Compare the application ABV with the alcohol percentage found on the label.
    """
    expected_values = extract_percentages(expected)

    if not expected_values:
        return {
            "status": "REVIEW",
            "detected_value": "No valid application percentage"
        }

    expected_value = expected_values[0]

    contextual_values = extract_alcohol_percentages(
        ocr_text
    )

    if contextual_values:

        for detected in contextual_values:
            if abs(expected_value - detected) <= 0.05:
                return {
                    "status": "MATCH",
                    "detected_value": f"{detected:g}%"
                }

        return {
            "status": "MISMATCH",
            "detected_value": f"{contextual_values[0]:g}%"
        }

    # A percentage without alcohol context is too ambiguous for MATCH or MISMATCH.
    generic_values = extract_percentages(
        ocr_text
    )

    for detected in generic_values:
        if abs(expected_value - detected) <= 0.05:
            return {
                "status": "REVIEW",
                "detected_value": (
                    f"{detected:g}% "
                    "(percentage detected, but alcohol context is unclear)"
                )
            }

    if generic_values:
        return {
            "status": "REVIEW",
            "detected_value": (
                f"{generic_values[0]:g}% "
                "(unrelated or uncertain percentage)"
            )
        }

    return {
        "status": "REVIEW",
        "detected_value": "Not confidently detected"
    }


def normalize_volume_unit(unit):
    """
    Convert different written volume units into one internal format.
    """
    if not unit:
        return None

    # Sometimes this function receives an already-normalized unit.
    if unit in {
        "ml",
        "cl",
        "l",
        "fl_oz",
    }:
        return unit

    cleaned = (
        str(unit)
        .lower()
        .replace(".", "")
        .replace(" ", "")
    )

    unit_map = {
        "ml": "ml",
        "milliliter": "ml",
        "milliliters": "ml",
        "millilitre": "ml",
        "millilitres": "ml",

        "cl": "cl",
        "centiliter": "cl",
        "centiliters": "cl",
        "centilitre": "cl",
        "centilitres": "cl",

        "l": "l",
        "liter": "l",
        "liters": "l",
        "litre": "l",
        "litres": "l",

        "floz": "fl_oz",
        "fluidounce": "fl_oz",
        "fluidounces": "fl_oz",
    }

    return unit_map.get(cleaned)


def convert_to_ml(number, unit):
    """
    Convert supported volume units to milliliters so they can be compared.
    """
    normalized_unit = normalize_volume_unit(
        unit
    )

    if normalized_unit == "ml":
        return number

    if normalized_unit == "cl":
        return number * 10.0

    if normalized_unit == "l":
        return number * 1000.0

    if normalized_unit == "fl_oz":
        return number * 29.5735295625

    return None


def extract_net_contents(text):
    """
    Read common beverage volume formats from OCR text.

    Examples:
    750 ml
    1 L
    1.5 fl. oz.
    1.5 fluid ounces
    """
    if not text:
        return []

    patterns = [
        (
            r"(?<!\d)"
            r"(\d+(?:\.\d+)?)"
            r"\s*"
            r"(fl\.?\s*oz\.?|fluid\s+ounces?)"
        ),
        (
            r"(?<!\d)"
            r"(\d+(?:\.\d+)?)"
            r"\s*"
            r"(ml|milliliters?|millilitres?)\b"
        ),
        (
            r"(?<!\d)"
            r"(\d+(?:\.\d+)?)"
            r"\s*"
            r"(cl|centiliters?|centilitres?)\b"
        ),
        (
            r"(?<!\d)"
            r"(\d+(?:\.\d+)?)"
            r"\s*"
            r"(l|liters?|litres?)\b"
        ),
    ]

    values = []

    for pattern in patterns:

        for match in re.finditer(
            pattern,
            text,
            flags=re.IGNORECASE
        ):
            try:
                number = float(
                    match.group(1)
                )
            except ValueError:
                continue

            if number <= 0:
                continue

            raw_unit = match.group(2)
            unit = normalize_volume_unit(
                raw_unit
            )

            if unit is None:
                continue

            ml_value = convert_to_ml(
                number,
                unit
            )

            if ml_value is None:
                continue

            values.append({
                "number": number,
                "unit": unit,
                "ml": ml_value,
                "raw": match.group(0).strip(),
                "start": match.start(),
                "end": match.end(),
            })

    # Remove exact duplicate readings while keeping the original order.
    unique_values = []
    seen = set()

    for value in values:
        key = (
            round(value["ml"], 2),
            value["unit"],
        )

        if key in seen:
            continue

        seen.add(key)
        unique_values.append(value)

    return unique_values


def format_volume(value):
    """
    Format a detected volume so it reads naturally in the UI.
    """
    number = value["number"]
    unit = value["unit"]

    if unit == "fl_oz":
        return (
            f"{number:g} fl. oz. "
            f"({value['ml']:.1f} mL)"
        )

    if unit == "ml":
        return f"{number:g} mL"

    if unit == "cl":
        return f"{number:g} cL"

    if unit == "l":
        return f"{number:g} L"

    return value["raw"]


def volume_is_in_serving_context(text, value):
    """
    Return True when a detected volume appears to describe a serving size.
    """
    if not text:
        return False

    start = value.get("start", 0)
    end = value.get("end", start)

    context_start = max(
        0,
        start - 90
    )

    context_end = min(
        len(text),
        end + 35
    )

    context = text[
        context_start:context_end
    ].lower()

    immediate_prefix = text[
        max(0, start - 45):start
    ].lower()

    if (
        "net contents" in immediate_prefix
        or "net content" in immediate_prefix
    ):
        return False

    serving_cues = [
        "serving size",
        "serving facts",
        "per serving",
        "servings per",
        "amount per serving",
    ]

    return any(
        cue in context
        for cue in serving_cues
    )


def verify_net_contents(expected, ocr_text):
    """
    Compare the application volume with a likely package volume on the label.

    Serving-size measurements are ignored because they do not prove the
    container's net contents. A small rounding difference is allowed when
    equivalent metric and fluid-ounce values are shown.
    """
    expected_values = extract_net_contents(
        expected
    )

    if not expected_values:
        return {
            "status": "REVIEW",
            "detected_value": "No valid application volume"
        }

    expected_volume = expected_values[0]
    expected_ml = expected_volume["ml"]

    detected_values = extract_net_contents(
        ocr_text
    )

    if not detected_values:
        return {
            "status": "REVIEW",
            "detected_value": "Not confidently detected"
        }

    serving_values = [
        value
        for value in detected_values
        if volume_is_in_serving_context(
            ocr_text,
            value
        )
    ]

    package_values = [
        value
        for value in detected_values
        if not volume_is_in_serving_context(
            ocr_text,
            value
        )
    ]

    if not package_values:
        serving_value = (
            format_volume(serving_values[0])
            if serving_values
            else "A volume"
        )

        return {
            "status": "REVIEW",
            "detected_value": (
                "Net contents not confidently detected; "
                f"{serving_value} appears in serving-size context"
            )
        }

    tolerance = max(
        1.0,
        expected_ml * 0.02
    )

    for detected in package_values:
        detected_ml = detected["ml"]

        if abs(expected_ml - detected_ml) <= tolerance:
            return {
                "status": "MATCH",
                "detected_value": format_volume(
                    detected
                )
            }

    return {
        "status": "MISMATCH",
        "detected_value": format_volume(
            package_values[0]
        )
    }


def warning_phrase_present(
    normalized_text,
    variants
):
    """
    Return True when at least one readable version of a warning phrase is present.
    """
    for variant in variants:
        normalized_variant = normalize_warning_text(
            variant
        )

        if (
            normalized_variant
            and normalized_variant
            in normalized_text
        ):
            return True

    return False


def verify_government_warning(ocr_text):
    """
    Check how much of the required government warning OCR actually captured.

    A clean full-text result can become MATCH.
    A noisy or partial warning stays REVIEW.
    I leave bold-formatting confirmation to the human reviewer because plain
    OCR text does not reliably prove whether the heading was visually bold.
    """
    detected = normalize_warning_text(
        ocr_text
    )

    if not detected:
        return {
            "status": "REVIEW",
            "detected_value":
                "Government warning not confidently detected"
        }

    required = normalize_warning_text(
        GOVERNMENT_WARNING
    )

    # OCR often drops the "(1)" and "(2)", so I do not require those numbers.
    required_without_numbers = re.sub(
        r"\b1\b|\b2\b",
        " ",
        required
    )

    required_without_numbers = re.sub(
        r"\s+",
        " ",
        required_without_numbers
    ).strip()

    if required_without_numbers in detected:
        return {
            "status": "MATCH",
            "detected_value": (
                "Required government warning wording detected; "
                "visual formatting still requires confirmation"
            )
        }

    has_heading = (
        "government warning"
        in detected
    )

    # OCR sometimes reads WARNING but misses the word GOVERNMENT.
    has_warning_word = (
        re.search(
            r"\bwarning\b",
            detected
        )
        is not None
    )

    # These phrase groups help us recognize a warning even when OCR
    # drops a few letters or words.
    phrase_groups = [
        [
            "surgeon general",
            "according to the surgeon",
        ],
        [
            "women should not drink",
        ],
        [
            "alcoholic beverages",
            "drink alcohol",
        ],
        [
            "during pregnancy",
            "pregnancy",
        ],
        [
            "risk of birth defects",
            "birth defects",
            "risk irth defects",
        ],
        [
            "consumption of alcoholic beverages",
            "consumption alcoholic",
        ],
        [
            "impairs your ability",
        ],
        [
            "drive a car",
            "drive car",
        ],
        [
            "operate machinery",
            "machinery",
        ],
        [
            "may cause health problems",
            "health problems",
        ],
    ]

    matched_groups = 0

    for variants in phrase_groups:
        if warning_phrase_present(
            detected,
            variants
        ):
            matched_groups += 1

    coverage = (
        matched_groups
        / len(phrase_groups)
    )

    if (
        has_heading
        and coverage >= 0.50
    ):
        return {
            "status": "REVIEW",
            "detected_value": (
                "Government warning detected, but exact "
                "wording/formatting requires manual review "
                f"({matched_groups}/"
                f"{len(phrase_groups)} phrase groups detected)"
            )
        }

    if (
        has_warning_word
        and coverage >= 0.40
    ):
        return {
            "status": "REVIEW",
            "detected_value": (
                "Possible government warning detected; "
                "OCR wording is incomplete "
                f"({matched_groups}/"
                f"{len(phrase_groups)} phrase groups detected)"
            )
        }

    if coverage >= 0.50:
        return {
            "status": "REVIEW",
            "detected_value": (
                "Government warning language partially detected; "
                "manual review required "
                f"({matched_groups}/"
                f"{len(phrase_groups)} phrase groups detected)"
            )
        }

    return {
        "status": "REVIEW",
        "detected_value":
            "Government warning not confidently detected"
    }


def scan_class_type(ocr_text):
    """
    Return the most specific known alcohol class/type found in OCR text.
    """
    normalized = normalize_text(
        ocr_text
    )

    sorted_types = sorted(
        ALCOHOL_TYPES,
        key=len,
        reverse=True
    )

    for alcohol_type in sorted_types:
        normalized_type = normalize_text(
            alcohol_type
        )

        pattern = (
            r"\b"
            + re.escape(normalized_type)
            + r"\b"
        )

        if re.search(
            pattern,
            normalized
        ):
            return alcohol_type.title()

    return None


def scan_alcohol_content(ocr_text):
    """
    Return ABV only when the percentage is tied to alcohol wording.
    """
    contextual = extract_alcohol_percentages(
        ocr_text
    )

    if contextual:
        return f"{contextual[0]:g}%"

    return None


def scan_net_contents(ocr_text):
    """
    Return a likely package volume without treating serving size as net contents.

    Scan Only mode stays conservative here because nutrition panels often include
    small serving volumes such as 1.5 fl. oz. (44 mL).
    """
    values = extract_net_contents(
        ocr_text
    )

    if not values:
        return None

    normalized_text = normalize_text(
        ocr_text
    )

    for value in values:
        raw = normalize_text(
            value["raw"]
        )

        position = normalized_text.find(
            raw
        )

        if position >= 0:
            context_start = max(
                0,
                position - 45
            )

            nearby_text = normalized_text[
                context_start:position
            ]

            if (
                "serving" in nearby_text
                or "per serving" in nearby_text
                or "serving size" in nearby_text
            ):
                continue

        # Small volumes are often serving-size measurements. Only accept them
        # when the label explicitly identifies them as net contents.
        if (
            value["ml"] < 100
            and "net contents" not in normalized_text
            and "net content" not in normalized_text
        ):
            continue

        return format_volume(
            value
        )

    return None


def scan_producer_name(ocr_text):
    """
    Return a producer or bottler name only when OCR captures a clear cue and name.
    """
    if not ocr_text:
        return None

    patterns = [
        r"(?:bottled\s+by)\s+"
        r"([A-Za-z0-9&.,'\- ]{3,80})",

        r"(?:produced\s+by)\s+"
        r"([A-Za-z0-9&.,'\- ]{3,80})",

        r"(?:brewed\s+by)\s+"
        r"([A-Za-z0-9&.,'\- ]{3,80})",

        r"(?:distilled\s+by)\s+"
        r"([A-Za-z0-9&.,'\- ]{3,80})",

        r"(?:imported\s+by)\s+"
        r"([A-Za-z0-9&.,'\- ]{3,80})",

        r"(?:packed\s+by)\s+"
        r"([A-Za-z0-9&.,'\- ]{3,80})",
    ]

    company_suffixes = {
        "co",
        "company",
        "llc",
        "inc",
        "corp",
        "corporation",
    }

    for pattern in patterns:
        match = re.search(
            pattern,
            ocr_text,
            re.IGNORECASE
        )

        if not match:
            continue

        candidate = (
            match
            .group(1)
            .strip()
        )

        words = candidate.split()[:10]

        meaningful_words = [
            re.sub(r"[^A-Za-z0-9]", "", word)
            for word in words
        ]

        meaningful_words = [
            word
            for word in meaningful_words
            if len(word) >= 3
            and word.lower() not in company_suffixes
        ]

        if (
            len(meaningful_words) >= 2
            and any(
                len(word) >= 4
                for word in meaningful_words
            )
        ):
            return " ".join(
                words
            )

    return None


def scan_origin_or_address(ocr_text):
    """
    Look for strong country-of-origin or production-location wording.
    """
    if not ocr_text:
        return None

    patterns = [
        r"product\s+of\s+"
        r"([A-Za-z][A-Za-z .,\-]{2,50})",

        r"made\s+in\s+"
        r"([A-Za-z][A-Za-z .,\-]{2,50})",

        r"imported\s+from\s+"
        r"([A-Za-z][A-Za-z .,\-]{2,50})",

        r"origin\s*:\s*"
        r"([A-Za-z][A-Za-z .,\-]{2,50})",

        r"bottled\s+in\s+the\s+"
        r"(united\s+states)",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            ocr_text,
            re.IGNORECASE
        )

        if match:
            candidate = (
                match
                .group(1)
                .strip()
            )

            words = candidate.split()

            candidate = " ".join(
                words[:8]
            )

            if len(candidate) >= 2:
                return candidate

    normalized = normalize_text(
        ocr_text
    )

    if "united states" in normalized:
        return "United States"

    # Do not infer "United States" from incomplete OCR such as "IN THE UNITED".
    return None


def scan_government_warning(ocr_text):
    """
    Reuse the warning verifier and return a simple result for Scan Only mode.
    """
    warning_result = verify_government_warning(
        ocr_text
    )

    status = warning_result[
        "status"
    ]

    detected_value = warning_result[
        "detected_value"
    ]

    if status == "MATCH":
        return "Government warning detected"

    if (
        "warning"
        in normalize_warning_text(
            ocr_text
        )
        or
        "surgeon"
        in normalize_warning_text(
            ocr_text
        )
    ):
        return detected_value

    return None


def find_known_ethiopian_brand(ocr_text):
    """
    Check the OCR text for one of the Ethiopian beer brands we know about.
    """
    normalized_ocr = normalize_text(
        ocr_text
    )

    for brand in ETHIOPIAN_BEER_BRANDS:
        normalized_brand = normalize_text(
            brand
        )

        if normalized_brand in normalized_ocr:
            return brand

    return None


def scan_brand_candidate(ocr_text):
    """
    Return a conservative brand candidate from OCR text.

    Without application data, the scanner only reports a brand when it finds a
    recognizable brand list entry or a reasonably clean company-style phrase.
    """
    if not ocr_text:
        return None

    known_ethiopian_brand = (
        find_known_ethiopian_brand(
            ocr_text
        )
    )

    if known_ethiopian_brand:
        return known_ethiopian_brand

    company_match = re.search(
        r"\b("
        r"[A-Z][A-Z0-9&'\-]*(?:\s+"
        r"[A-Z][A-Z0-9&'\-]*){1,5}\s+"
        r"(?:CO\.?|COMPANY|LLC|INC\.?|CORP\.?)"
        r")\b",
        ocr_text
    )

    if not company_match:
        return None

    company_name = (
        company_match
        .group(1)
        .strip()
    )

    cleaned = re.sub(
        r"\s+"
        r"(?:RUM|VODKA|GIN|WHISKEY|WHISKY|BEER|WINE)?"
        r"\s*"
        r"(?:CO\.?|COMPANY|LLC|INC\.?|CORP\.?)$",
        "",
        company_name,
        flags=re.IGNORECASE
    ).strip()

    words = cleaned.split()

    # OCR sometimes attaches a short fragment from the word before the brand.
    # Trim those fragments instead of presenting them as part of the brand.
    while (
        len(words) > 2
        and len(re.sub(r"[^A-Za-z]", "", words[0])) <= 4
    ):
        words.pop(0)

    if len(words) < 2:
        return None

    if any(
        len(re.sub(r"[^A-Za-z]", "", word)) < 3
        for word in words
    ):
        return None

    return (
        "Possible: "
        + " ".join(words).title()
    )



def find_detected_alcohol_type(ocr_text):
    """
    Look for a known alcohol class/type in one OCR text block.

    I use this for front-label checks so LabelGuard can notice an obvious
    conflict such as the application saying Rum while the front label says Vodka.
    """
    normalized = normalize_text(
        ocr_text
    )

    if not normalized:
        return None

    # Check longer names first so "Ethiopian Honey Wine" wins over "Wine".
    for alcohol_type in sorted(
        ALCOHOL_TYPES,
        key=len,
        reverse=True
    ):
        normalized_type = normalize_text(
            alcohol_type
        )

        if re.search(
            r"\b"
            + re.escape(normalized_type)
            + r"\b",
            normalized
        ):
            return alcohol_type

    return None


def verify_brand_by_label_side(
    expected,
    front_ocr_text,
    back_ocr_text
):
    """
    Brand name is mainly a front-label check.

    If the exact brand is on the front, it is a MATCH.
    If it only appears on the back, I keep it at REVIEW instead of letting
    back-label company text create a false front-label match.
    """
    front_result = verify_text_field(
        expected,
        front_ocr_text
    )

    if front_result["status"] == "MATCH":
        return front_result

    expected_normalized = normalize_text(
        expected
    )

    back_normalized = normalize_text(
        back_ocr_text
    )

    if (
        expected_normalized
        and expected_normalized in back_normalized
    ):
        return {
            "status": "REVIEW",
            "detected_value": (
                f"{expected} found on back label, "
                "but not confidently detected on front label"
            )
        }

    return front_result


def verify_class_type_by_label_side(
    expected,
    front_ocr_text,
    back_ocr_text
):
    """
    Check class/type mainly from the front label.

    I do not treat a broad word such as "Rum" as a contradiction when the
    application says "Spiced Rum". If the front clearly shows a different
    product type such as Vodka, that is a real mismatch.
    """
    expected_normalized = normalize_text(
        expected
    )

    front_normalized = normalize_text(
        front_ocr_text
    )

    if not expected_normalized:
        return {
            "status": "REVIEW",
            "detected_value": "No application value provided"
        }

    # Best case: the full application type appears as one phrase.
    if expected_normalized in front_normalized:
        return {
            "status": "MATCH",
            "detected_value": expected
        }

    # OCR often separates words that are next to each other on the label.
    # For example, "SPICED" and "RUM" may both be present but not adjacent.
    expected_words = [
        word
        for word in expected_normalized.split()
        if len(word) >= 3
        and word not in {"alcohol", "beverage", "beverages"}
    ]

    front_words = set(
        front_normalized.split()
    )

    if expected_words:
        word_matches = []

        for expected_word in expected_words:
            exact_match = (
                expected_word in front_words
            )

            fuzzy_match = any(
                similarity(
                    expected_word,
                    front_word
                ) >= 0.82
                for front_word in front_words
                if len(front_word) >= 3
            )

            word_matches.append(
                exact_match or fuzzy_match
            )

        # Small OCR errors such as "yspiced" should not turn
        # "Spiced Rum" into a false mismatch.
        if all(word_matches):
            return {
                "status": "MATCH",
                "detected_value": expected
            }

    detected_front_type = find_detected_alcohol_type(
        front_ocr_text
    )

    if detected_front_type:
        detected_normalized = normalize_text(
            detected_front_type
        )

        if detected_normalized == expected_normalized:
            return {
                "status": "MATCH",
                "detected_value": expected
            }

        # "Rum" does not contradict "Spiced Rum"; it just means OCR did not
        # confidently capture the full subtype.
        if (
            detected_normalized
            and detected_normalized in expected_normalized
        ):
            return {
                "status": "REVIEW",
                "detected_value": (
                    f"{detected_front_type.title()} detected; "
                    f"full type '{expected}' was not confidently read"
                )
            }

        # A clearly different type on the front is strong evidence of a mismatch.
        return {
            "status": "MISMATCH",
            "detected_value": detected_front_type.title()
        }

    # If the requested type appears only on the back, keep it for review.
    back_normalized = normalize_text(
        back_ocr_text
    )

    if (
        expected_normalized
        and expected_normalized in back_normalized
    ):
        return {
            "status": "REVIEW",
            "detected_value": (
                f"{expected} found on back label, "
                "but not confidently detected on front label"
            )
        }

    return verify_text_field(
        expected,
        front_ocr_text
    )



def extract_scan_fields(ocr_text):
    """
    Build the structured result shown in Scan Label Only mode.
    """
    return {
        "brand_name":
            scan_brand_candidate(
                ocr_text
            ),

        "class_type":
            scan_class_type(
                ocr_text
            ),

        "alcohol_content":
            scan_alcohol_content(
                ocr_text
            ),

        "net_contents":
            scan_net_contents(
                ocr_text
            ),

        "producer_name":
            scan_producer_name(
                ocr_text
            ),

        "producer_address":
            scan_origin_or_address(
                ocr_text
            ),

        "government_warning":
            scan_government_warning(
                ocr_text
            ),
    }


def verify_fields(
    front_ocr_text: str,
    back_ocr_text: str,
    brand_name: str,
    class_type: str,
    alcohol_content: str,
    net_contents: str,
    producer_name: str,
    producer_address: str
):
    """
    Run each check against the label side where that information is most useful.

    Brand and class/type are checked mainly on the front.
    ABV, volume, producer information, origin, and the government warning are
    checked mainly on the back. If there is no back image, I fall back to the
    front OCR so a single-label upload can still be reviewed.
    """
    combined_ocr_text = (
        front_ocr_text
        + "\n"
        + back_ocr_text
    ).strip()

    detail_ocr_text = (
        back_ocr_text.strip()
        if back_ocr_text and back_ocr_text.strip()
        else combined_ocr_text
    )

    return {
        "brand_name":
            verify_brand_by_label_side(
                brand_name,
                front_ocr_text,
                back_ocr_text
            ),

        "class_type":
            verify_class_type_by_label_side(
                class_type,
                front_ocr_text,
                back_ocr_text
            ),

        "alcohol_content":
            verify_alcohol_content(
                alcohol_content,
                detail_ocr_text
            ),

        "net_contents":
            verify_net_contents(
                net_contents,
                detail_ocr_text
            ),

        "producer_name":
            verify_text_field(
                producer_name,
                detail_ocr_text
            ),

        "producer_address":
            verify_text_field(
                producer_address,
                detail_ocr_text
            ),

        "government_warning":
            verify_government_warning(
                detail_ocr_text
            ),
    }
