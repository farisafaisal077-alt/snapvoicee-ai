const BACKEND_URL = "https://snapvoicee-ai.onrender.com";

const photoInput = document.getElementById("photoInput");
const photoPreview = document.getElementById("photoPreview");
const generateButton = document.getElementById("generateButton");
const statusText = document.getElementById("status");

let selectedPhoto = null;

// Select and preview a photo
photoInput.addEventListener("change", function () {
    const file = photoInput.files[0];

    if (!file) {
        selectedPhoto = null;
        generateButton.disabled = true;
        return;
    }

    if (!file.type.startsWith("image/")) {
        statusText.textContent = "Please select an image.";
        photoInput.value = "";
        selectedPhoto = null;
        generateButton.disabled = true;
        return;
    }

    if (file.size > 5 * 1024 * 1024) {
        statusText.textContent =
            "Please select an image smaller than 5 MB.";
        photoInput.value = "";
        selectedPhoto = null;
        generateButton.disabled = true;
        return;
    }

    selectedPhoto = file;

    photoPreview.src = URL.createObjectURL(file);
    photoPreview.style.display = "block";

    generateButton.disabled = false;

    statusText.textContent =
        "Photo selected successfully. Ready to generate!";
});

// Generate content using the AI backend
generateButton.addEventListener("click", async function () {
    if (!selectedPhoto) {
        statusText.textContent = "Please select a photo first.";
        return;
    }

    const styleSelect = document.getElementById("styleSelect");
    const formData = new FormData();

    formData.append("photo", selectedPhoto);
    formData.append("style", styleSelect.value);

    generateButton.disabled = true;
    statusText.textContent =
        "AI is analyzing your photo. Please wait...";

    try {
        const response = await fetch(
            `${BACKEND_URL}/generate`,
            {
                method: "POST",
                body: formData
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.error || "AI content generation failed."
            );
        }

        document.getElementById("caption").textContent =
            data.caption;

        document.getElementById("hashtags").textContent =
            data.hashtags;

        document.getElementById("description").textContent =
            data.description;

        document.getElementById("song").textContent =
            data.song;

        statusText.textContent =
            "Success! Your AI content is ready.";

    } catch (error) {
        console.error("SnapVoice AI error:", error);

        statusText.textContent =
            error.message ||
            "Unable to connect. Please try again.";
    } finally {
        generateButton.disabled = false;
    }
});

// Copy generated content
document.querySelectorAll(".copy-button").forEach(function (button) {
    button.addEventListener("click", async function () {
        const target = document.getElementById(button.dataset.target);

        if (!target) {
            statusText.textContent = "Content not found.";
            return;
        }

        try {
            await navigator.clipboard.writeText(target.textContent);
            statusText.textContent = "Copied successfully!";
        } catch (error) {
            statusText.textContent =
                "Copy failed. Please select and copy the text manually.";
        }
    });
});
