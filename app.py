
import os
import json
import base64
import logging
import time
from io import BytesIO

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from PIL import Image, UnidentifiedImageError

load_dotenv()

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# Allow GitHub Pages to access this backend.
CORS(
    app,
    resources={
        r"/generate": {
            "origins": [
                "https://farisafaisal077-alt.github.io"
            ]
        }
    }
)

app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

# Gemini settings from Render Environment.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.8-flash"
)

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models/"
    + GEMINI_MODEL
    + ":generateContent"
)

STYLES = {
    "Casual": "casual and natural",
    "Funny": "funny and playful",
    "Aesthetic": "aesthetic and minimal",
    "Romantic": "romantic and emotional",
    "Professional": "professional and polished"
}

RETRYABLE_STATUSES = (429, 500, 502, 503, 504)
MAX_ATTEMPTS = 3


@app.get("/")
def home():
    return jsonify({
        "message": "SnapVoice AI Gemini backend is running!",
        "model": GEMINI_MODEL
    })


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "message": "Backend is running."
    })


@app.errorhandler(413)
def file_too_large(error):
    return jsonify({
        "error": "Image must be smaller than 5 MB."
    }), 413


def call_gemini(payload):
    """Call Gemini and retry temporary errors and timeouts."""
    last_response = None

    for attempt in range(MAX_ATTEMPTS):
        try:
            response = requests.post(
                GEMINI_URL,
                params={"key": GEMINI_API_KEY},
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=90
            )

            last_response = response

            if response.ok:
                return response, None

            if response.status_code not in RETRYABLE_STATUSES:
                return response, None

            if attempt == MAX_ATTEMPTS - 1:
                break

            wait_seconds = 2 ** (attempt + 1)

            app.logger.warning(
                "Gemini returned HTTP %s. "
                "Retrying in %s seconds (attempt %s of %s).",
                response.status_code,
                wait_seconds,
                attempt + 2,
                MAX_ATTEMPTS
            )

            time.sleep(wait_seconds)

        except requests.Timeout:
            if attempt == MAX_ATTEMPTS - 1:
                return None, "timeout"

            wait_seconds = 2 ** (attempt + 1)

            app.logger.warning(
                "Gemini timed out. Retrying in %s seconds.",
                wait_seconds
            )

            time.sleep(wait_seconds)

        except requests.RequestException:
            app.logger.exception("Gemini connection failed.")

            if attempt == MAX_ATTEMPTS - 1:
                return None, "connection"

            time.sleep(2 ** (attempt + 1))

    return last_response, None


@app.post("/generate")
def generate():

    if not GEMINI_API_KEY:
        return jsonify({
            "error": (
                "Gemini API key is missing. "
                "Add GEMINI_API_KEY in Render Environment."
            )
        }), 500

    photo = request.files.get("photo")

    if not photo:
        return jsonify({
            "error": "Please upload a photo."
        }), 400

    style_name = request.form.get("style", "Casual")
    style = STYLES.get(style_name, STYLES["Casual"])

    personal_example = request.form.get(
        "personal_example", ""
    ).strip()[:500]

    # Validate and prepare the uploaded image.
    try:
        image = Image.open(photo.stream)

        if image.format not in ("JPEG", "PNG", "WEBP"):
            return jsonify({
                "error": "Only JPG, PNG and WEBP images are supported."
            }), 400

        image.verify()
        photo.stream.seek(0)

        image = Image.open(photo.stream).convert("RGB")
        image.thumbnail((1024, 1024))

        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=85)

        encoded_image = base64.b64encode(
            buffer.getvalue()
        ).decode("utf-8")

    except (
        UnidentifiedImageError,
        OSError,
        ValueError
    ):
        return jsonify({
            "error": "The uploaded file is not a valid image."
        }), 400

    prompt = f"""
You are SnapVoice AI, a photo-content assistant.

Analyze the uploaded image and generate:

1. caption: An engaging social media caption.
2. hashtags: Five to ten relevant hashtags.
3. description: An accurate description of the image.
4. song: A suitable song suggestion or music genre,
   with a short explanation of why it fits.

Writing style: {style}

User's writing examples:
{personal_example}

Rules:
- Do not invent details that cannot be established
  from the image.
- Do not identify people in the image.
- Return valid JSON only.
- All four values must be strings.
- Do not claim that a song is licensed or available
  on a particular streaming service.

Return exactly this JSON structure:

{{
  "caption": "Your caption",
  "hashtags": "#tag1 #tag2 #tag3 #tag4 #tag5",
  "description": "Your image description",
  "song": "Song or music suggestion and explanation"
}}
"""

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": encoded_image
                        }
                    }
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "maxOutputTokens": 1200
        }
    }

    # Call Gemini with automatic retries.
    response, failure = call_gemini(payload)

    if failure == "timeout":
        return jsonify({
            "error": (
                "Gemini timed out after several attempts. "
                "Please try again shortly."
            )
        }), 504

    if failure == "connection":
        return jsonify({
            "error": (
                "Could not connect to Gemini after several attempts. "
                "Please try again shortly."
            )
        }), 502

    if response is None:
        return jsonify({
            "error": "Gemini did not return a response."
        }), 502

    if not response.ok:
        app.logger.error(
            "Gemini API returned HTTP %s: %s",
            response.status_code,
            response.text[:1000]
        )

        if response.status_code == 429:
            return jsonify({
                "error": (
                    "Gemini request limit reached. "
                    "Check your API quota and billing."
                )
            }), 429

        if response.status_code in (401, 403):
            return jsonify({
                "error": (
                    "Gemini API authentication failed. "
                    "Check your API key and permissions."
                )
            }), 502

        if response.status_code == 404:
            return jsonify({
                "error": (
                    "Gemini model not found. "
                    "Check GEMINI_MODEL in Render Environment."
                )
            }), 502

        if response.status_code in RETRYABLE_STATUSES:
            return jsonify({
                "error": (
                    "Gemini is still busy after several attempts. "
                    "Please try again shortly."
                )
            }), 503

        return jsonify({
            "error": (
                "Gemini request failed. "
                "Check the Render application logs."
            )
        }), 502

    try:
        result = response.json()
        candidates = result.get("candidates", [])

        if not candidates:
            app.logger.error("Gemini returned no candidates.")

            return jsonify({
                "error": (
                    "Gemini returned no content. "
                    "Please try another photo."
                )
            }), 502

        parts = candidates[0].get(
            "content", {}
        ).get("parts", [])

        output_text = "".join(
            part.get("text", "")
            for part in parts
            if isinstance(part.get("text"), str)
        )

        if not output_text.strip():
            return jsonify({
                "error": "Gemini returned an empty response."
            }), 502

        data = json.loads(output_text)

        required_fields = [
            "caption",
            "hashtags",
            "description",
            "song"
        ]

        for field in required_fields:
            if (
                not isinstance(data.get(field), str)
                or not data[field].strip()
            ):
                raise ValueError(
                    "Missing or invalid field: " + field
                )

        return jsonify({
            field: data[field]
            for field in required_fields
        })

    except (ValueError, json.JSONDecodeError):
        app.logger.exception(
            "Could not parse the Gemini response."
        )

        return jsonify({
            "error": (
                "Could not process the AI response. "
                "Please try again."
            )
        }), 502

    except requests.RequestException:
        app.logger.exception("Error processing Gemini response.")

        return jsonify({
            "error": "Could not process the Gemini response."
        }), 502


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )
