import os
import json
import base64
import requests

from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
from io import BytesIO

app = Flask(__name__)

app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

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

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "SnapVoice AI Gemini backend is running!"
    })


@app.route("/generate", methods=["POST"])
def generate():
    if not GEMINI_API_KEY:
        return jsonify({
            "error": "Gemini API key is missing in Render."
        }), 500

    if "photo" not in request.files:
        return jsonify({
            "error": "Please upload a photo."
        }), 400

    photo = request.files["photo"]
    style = request.form.get("style", "aesthetic")

    if not photo.filename:
        return jsonify({
            "error": "Please select an image."
        }), 400

    try:
        image_bytes = photo.read()

        if not image_bytes:
            return jsonify({
                "error": "The uploaded image is empty."
            }), 400

        # Validate the image and determine its actual format.
        with Image.open(BytesIO(image_bytes)) as image:
            image_format = image.format
            image.verify()

        mime_types = {
            "JPEG": "image/jpeg",
            "PNG": "image/png",
            "WEBP": "image/webp"
        }

        if image_format not in mime_types:
            return jsonify({
                "error": "Please upload a JPG, PNG, or WEBP image."
            }), 400

        mime_type = mime_types[image_format]

        encoded_image = base64.b64encode(
            image_bytes
        ).decode("utf-8")

        prompt = f"""
You are SnapVoice AI, an assistant that creates social media
content from photos.

Analyze the uploaded image and generate content in this style:
{style}

Return ONLY a valid JSON object with these four fields:

{{
  "caption": "A suitable caption for the photo",
  "hashtags": "#tag1 #tag2 #tag3",
  "description": "A factual description of the visible image",
  "song": "A suitable song suggestion"
}}

Requirements:
- Make the caption relevant to the actual image.
- Make the hashtags relevant to the image.
- Describe only things that can reasonably be seen.
- Suggest a song that matches the mood of the image.
- Do not include Instagram upload or publishing instructions.
- Return JSON only.
"""

        api_url = (
            "https://generativelanguage.googleapis.com/"
            f"v1beta/models/{GEMINI_MODEL}:generateContent"
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": encoded_image
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.7
            }
        }

        response = requests.post(
            api_url,
            headers={
                "x-goog-api-key": GEMINI_API_KEY,
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=60
        )

        if not response.ok:
            print("Gemini API error:", response.status_code, response.text)

            return jsonify({
                "error": (
                    "Gemini request failed. Check your API key, "
                    "model availability, quota, and Render logs."
                )
            }), 502

        result = response.json()

        candidates = result.get("candidates", [])

        if not candidates:
            return jsonify({
                "error": "Gemini did not return a result."
            }), 502

        parts = candidates[0].get("content", {}).get("parts", [])

        generated_text = "".join(
            part.get("text", "")
            for part in parts
        ).strip()

        if not generated_text:
            return jsonify({
                "error": "Gemini returned an empty response."
            }), 502

        # Handle JSON returned by Gemini.
        content = json.loads(generated_text)

        return jsonify({
            "caption": content.get("caption", ""),
            "hashtags": content.get("hashtags", ""),
            "description": content.get("description", ""),
            "song": content.get("song", "")
        })

    except json.JSONDecodeError:
        return jsonify({
            "error": "Gemini returned an unexpected response format."
        }), 502

    except Exception as error:
        print("Backend error:", str(error))

        return jsonify({
            "error": "Something went wrong while processing the image."
        }), 500


@app.errorhandler(413)
def file_too_large(error):
    return jsonify({
        "error": "Image is too large. Maximum size is 5 MB."
    }), 413


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
