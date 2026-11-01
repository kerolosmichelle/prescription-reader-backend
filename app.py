"""Flask API for the Roshtaty prescription reader.

Serves the single-page frontend and exposes an OCR endpoint that returns the
raw text plus a structured list of medicines.
"""

import os
import time
import uuid

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.exceptions import RequestEntityTooLarge

from ocr import LANGUAGE, read_prescription
from parser import parse_prescription
try:
    from services.medicine_matcher import MedicineMatcher
except Exception as e:
    MedicineMatcher = None
    print(f"Medicine matcher not available: {e}")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Look for the frontend inside the backend folder first (used on Render),
# then fall back to the sibling ../frontend folder (used on your own PC).
_inside_frontend = os.path.join(BASE_DIR, "frontend")
_sibling_frontend = os.path.normpath(os.path.join(BASE_DIR, "..", "frontend"))
FRONTEND_DIR = _inside_frontend if os.path.isdir(_inside_frontend) else _sibling_frontend

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "bmp", "tif", "tiff", "webp"}
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "10"))

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024
CORS(app)

try:
    from api.v1.routes.medicines import api_v1
    app.register_blueprint(api_v1)
    try:
        from api.v1.routes.safety import safety_bp
        app.register_blueprint(safety_bp)
    except Exception as e2:
        print(f"safety not registered: {e2}")
    print("API v1 registered")
except Exception as e:
    print(f"API v1 not registered: {e}")


def _error(message, status=400, code=None):
    return jsonify({"success": False, "error": message, "code": code}), status


def _extension(filename):
    return os.path.splitext(filename)[1].lstrip(".").lower()


@app.route("/", methods=["GET"])
def home():
    index = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index):
        return send_from_directory(FRONTEND_DIR, "index.html")
    return jsonify({"message": "Roshtaty OCR API is running"})


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify(
        {
            "success": True,
            "status": "ok",
            "ocr_language": LANGUAGE,
            "max_upload_mb": MAX_UPLOAD_MB,
        }
    )


@app.route("/extract-text", methods=["POST"])
@app.route("/api/extract", methods=["POST"])
def extract_text_api():
    started = time.perf_counter()

    if "image" not in request.files:
        return _error("No image provided. Send the file as form field 'image'.", 400, "missing_file")

    file = request.files["image"]

    if not file.filename:
        return _error("No file selected.", 400, "empty_filename")

    extension = _extension(file.filename)
    if extension not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        return _error(f"Unsupported file type. Allowed: {allowed}.", 415, "unsupported_type")

    filename = f"{uuid.uuid4().hex}.{extension}"
    image_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(image_path)

    try:
        ocr_result = read_prescription(image_path)

        raw_text = ocr_result["text"]
        if not raw_text:
            return _error(
                "No readable text was found. Try a sharper, well-lit photo.",
                422,
                "no_text",
            )

        parsed = parse_prescription(raw_text)
        medicines = parsed["medicines"]
        try:
            if MedicineMatcher is not None:
                matcher = MedicineMatcher()
                try:
                    medicines = matcher.enrich_medicines(medicines)
                finally:
                    matcher.close()
        except Exception as e:
            app.logger.exception("Medicine matching failed")
            print(f"Medicine matching failed: {e}")

        return jsonify(
            {
                "success": True,
                "filename": file.filename,
                "raw_text": raw_text,
                "confidence": ocr_result["confidence"],
                "word_count": ocr_result["word_count"],
                "language": ocr_result["language"],
                "medicines": medicines,
                "patient": parsed["patient"],
                "processing_ms": round((time.perf_counter() - started) * 1000),
            }
        )

    except ValueError as exc:
        return _error(str(exc), 422, "invalid_image")
    except Exception as exc:  # pragma: no cover - surfaced to the client
        app.logger.exception("OCR failed")
        return _error(f"OCR failed: {exc}", 500, "ocr_failed")

    finally:
        if os.path.exists(image_path):
            try:
                os.remove(image_path)
            except OSError:
                pass


@app.errorhandler(RequestEntityTooLarge)
def handle_large_file(_error_obj):
    return _error(
        f"File is too large. The limit is {MAX_UPLOAD_MB} MB.",
        413,
        "file_too_large",
    )


@app.errorhandler(404)
def handle_not_found(_error_obj):
    if request.path.startswith("/api") or request.path == "/extract-text":
        return _error("Endpoint not found.", 404, "not_found")

    # A missing static file (with an extension) is a real 404, not the SPA.
    if "." in os.path.basename(request.path):
        return _error("File not found.", 404, "not_found")

    # Only fall back to the SPA page if it actually exists on this server.
    index = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index):
        return send_from_directory(FRONTEND_DIR, "index.html")
    return _error("File not found.", 404, "not_found")


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
        debug=debug,
        use_reloader=debug,
    )   