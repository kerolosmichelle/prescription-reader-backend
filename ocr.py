"""Image preprocessing and OCR for prescription images."""

import os
import shutil

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageOps
from pytesseract import Output

# ---------------------------------------------------------------------------
# Tesseract discovery
# ---------------------------------------------------------------------------

WINDOWS_TESSERACT_PATHS = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
)


def _configure_tesseract():
    """Point pytesseract at a local Tesseract install when it is not on PATH."""

    configured = os.environ.get("TESSERACT_CMD")
    if configured and os.path.exists(configured):
        pytesseract.pytesseract.tesseract_cmd = configured
        return

    if shutil.which("tesseract"):
        return

    for candidate in WINDOWS_TESSERACT_PATHS:
        if os.path.exists(candidate):
            pytesseract.pytesseract.tesseract_cmd = candidate
            return


_configure_tesseract()

OCR_LANG = os.environ.get("OCR_LANG", "eng+ara")

# Languages we request from Tesseract. Missing traineddata files are dropped so
# the app still works on a default (English-only) Tesseract installation.
ocr_languages = [lang.strip() for lang in OCR_LANG.split("+") if lang.strip()]
try:
    available_languages = set(pytesseract.get_languages(config=""))
    ocr_languages = [lang for lang in ocr_languages if lang in available_languages]
except Exception:  # pragma: no cover - tesseract not installed
    available_languages = set()

if not ocr_languages:
    ocr_languages = ["eng"]

LANGUAGE = "+".join(ocr_languages)


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------

def load_image(image_path):
    """Read an image, respecting EXIF orientation, as a BGR numpy array."""

    with Image.open(image_path) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        rgb = np.array(image)

    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def _upscale(image):
    height, width = image.shape[:2]

    # Keep very large phone photos reasonable while making small scans readable.
    scale = max(1.0, 1600 / max(width, 1))
    scale = min(scale, 3.0)

    longest = max(height, width) * scale
    if longest > 4000:
        scale *= 4000 / longest

    if abs(scale - 1.0) < 0.01:
        return image

    return cv2.resize(
        image,
        None,
        fx=scale,
        fy=scale,
        interpolation=cv2.INTER_CUBIC,
    )


def _variants(image):
    """Return a few preprocessed candidates; OCR picks the most confident one."""

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = _upscale(gray)

    # Reduce sensor noise from phone photos without destroying thin strokes.
    denoised = cv2.fastNlMeansDenoising(gray, None, 7, 7, 21)
    denoised = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(denoised)

    otsu = cv2.threshold(
        denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )[1]

    adaptive = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11,
    )

    return [adaptive, otsu, denoised, gray]


# ---------------------------------------------------------------------------
# OCR
# ---------------------------------------------------------------------------

def _ocr(image, psm):
    """Run one Tesseract pass and rebuild line-structured text plus confidence."""

    config = f"--oem 3 --psm {psm}"

    data = pytesseract.image_to_data(
        image,
        lang=LANGUAGE,
        config=config,
        output_type=Output.DICT,
    )

    grouped = {}
    confidences = []
    word_count = 0

    for text, confidence, block, paragraph, line in zip(
        data["text"],
        data["conf"],
        data["block_num"],
        data["par_num"],
        data["line_num"],
    ):
        text = text.strip()
        if not text:
            continue

        grouped.setdefault((block, paragraph, line), []).append(text)
        word_count += 1

        confidence = float(confidence)
        if confidence >= 0:
            # Longer words are more meaningful, weight them a little more.
            confidences.extend([confidence] * min(len(text), 8))

    # Tesseract returns words in reading order; grouping keeps line breaks.
    text = "\n".join(
        " ".join(words) for _, words in sorted(grouped.items())
    ).strip()

    confidence = round(sum(confidences) / len(confidences), 1) if confidences else 0.0

    return {
        "text": text,
        "confidence": confidence,
        "word_count": word_count,
    }


def extract_text(image_path):
    """Backwards-compatible helper: return only the raw extracted text."""

    return read_prescription(image_path)["text"]


def read_prescription(image_path):
    """Run OCR on a prescription image and return text plus a confidence score.

    The first variant and page-segmentation mode handle the common case. Clean
    scans stop there; only difficult photos fall back to extra passes.
    """

    image = load_image(image_path)

    if image is None or image.size == 0:
        raise ValueError("Could not read image")

    variants = _variants(image)

    best = None
    best_index = 0

    for index, candidate in enumerate(variants):
        try:
            result = _ocr(candidate, 6)
        except pytesseract.TesseractNotFoundError as exc:
            raise RuntimeError(
                "Tesseract OCR is not installed. Install it and add it to PATH."
            ) from exc

        if result["text"]:
            score = result["confidence"] + min(result["word_count"], 60) * 0.05
            if best is None or score > best["score"]:
                best = {**result, "score": score}
                best_index = index

        # A confident first pass with real content is good enough.
        if index == 0 and result["confidence"] >= 78 and len(result["text"]) >= 30:
            break

    # Hard images: try a different segmentation mode on the best variant.
    if best and best["confidence"] < 70:
        try:
            alternative = _ocr(variants[best_index], 4)
        except pytesseract.TesseractNotFoundError as exc:
            raise RuntimeError(
                "Tesseract OCR is not installed. Install it and add it to PATH."
            ) from exc

        if alternative["text"]:
            score = alternative["confidence"] + min(alternative["word_count"], 60) * 0.05
            if score > best["score"]:
                best = {**alternative, "score": score}

    if best is None:
        return {"text": "", "confidence": 0.0, "word_count": 0, "language": LANGUAGE}

    return {
        "text": best["text"],
        "confidence": best["confidence"],
        "word_count": best["word_count"],
        "language": LANGUAGE,
    }
