import os
import json
import base64
from io import BytesIO

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from PIL import Image, UnidentifiedImageError

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/generate": {"origins": [
    "https://farisafaisal077-alt.github.io"
]}})

app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL")

STYLES = {
    "Casual": "casual and natural",
    "Funny": "funny and playful",
    "Aesthetic": "aesthetic and minimal",
    "Romantic": "romantic and emotional",
    "Professional": "professional and polished",
}


@app.get("/")
def home():
    return jsonify({
        "message": "SnapVoice AI backend is running."
    })


@app.errorhandler(413)
def file_too_large(error):
    return jsonify({
        "error": "Image must be smaller than 5 MB."
    }), 413


@app.post("/generate")
def generate():
    if not API_KEY or not MODEL:
        return jsonify({
            "error": "API configuration is missing."
        }), 500

    photo = request.files.get("photo")

    if not photo:
        return jsonify({
            "error": "Please upload a photo."
        }), 400

    style = request.form.get("style", "Casual")
    style = STYLES.get(style, STYLES["Casual"])

    personal_example = request.form.get(
        "personal_example", ""
    ).strip()[:500]

    try:
        image = Image.open(photo.stream)

        if image.format not in ("JPEG", "PNG", "WEBP"):
            return jsonify({
                "error": "Only JPG, PNG and WEBP are supported."
            }), 400

        image.verify()

        photo.stream.seek(0)
        image = Image.open(photo.stream).convert("RGB")
        image.thumbnail((1024, 1024))

        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=85)

        encoded = base64.b64encode(
            buffer.getvalue()
        ).decode("utf-8")

    except (UnidentifiedImageError, OSError, ValueError):
        return jsonify({
            "error": "The uploaded file is not a valid image."
        }), 400

    prompt = f"""
You are SnapVoice, an AI photo-content assistant.

Analyze the uploaded photo and return:
1. caption: an engaging social-media caption.
2. hashtags: 5-10 relevant hashtags.
3. description: an accurate description of the photo.
4. song: a suitable song or music genre and why it fits.

Writing style: {style}.

Do not invent details that cannot be established from the image.
Do not identify people in the photo.
For the song, provide a suggestion; do not claim that it is licensed
or available on any particular streaming service.

User's writing examples, if provided:
{personal_example}

Return a JSON object with exactly these string fields:
caption, hashtags, description, song.
"""

    payload = {
        "model": MODEL,
        "input": [{
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": prompt
                },
                {
                    "type": "input_image",
                    "image_url": (
                        "data:image/jpeg;base64," + encoded
                    ),
                    "detail": "auto"
                }
            ]
        }],
        "max_output_tokens": 700,
        "text": {
            "format": {
                "type": "json_object"
            }
        }
    }

    try:
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=90
        )

        if not response.ok:
            app.logger.error(
                "AI API returned status %s",
                response.status_code
            )
            return jsonify({
                "error": (
                    "AI request failed. Check the backend logs, "
                    "model access and API billing."
                )
            }), 502

        result = response.json()
        output_text = ""

        for item in result.get("output", []):
            if item.get("type") == "message":
                for content in item.get("content", []):
                    if content.get("type") == "output_text":
                        output_text += content.get("text", "")

        data = json.loads(output_text)

        fields = ["caption", "hashtags", "description", "song"]

        if not all(
            isinstance(data.get(field), str)
            and data[field].strip()
            for field in fields
        ):
            raise ValueError("Incomplete AI response")

        return jsonify({
            field: data[field] for field in fields
        })

    except requests.RequestException:
        app.logger.exception("AI connection failed")
        return jsonify({
            "error": "Could not connect to the AI service."
        }), 502

    except (ValueError, json.JSONDecodeError):
        app.logger.exception("Invalid AI response")
        return jsonify({
            "error": "Could not process the AI response."
        }), 502


if __name__ == "__main__":
    app.run()
