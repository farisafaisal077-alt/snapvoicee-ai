const photoInput = document.getElementById("photoInput");
const photoPreview = document.getElementById("photoPreview");
const generateButton = document.getElementById("generateButton");
const statusText = document.getElementById("status");

let selectedPhoto = null;

photoInput.addEventListener("change", function () {
    const file = photoInput.files[0];

    if (!file) {
        return;
    }

    if (!file.type.startsWith("image/")) {
        statusText.textContent = "Please select an image.";
        return;
    }

    if (file.size > 10 * 1024 * 1024) {
        statusText.textContent =
            "Please select an image smaller than 10 MB.";
        photoInput.value = "";
        return;
    }

    selectedPhoto = file;

    const imageURL = URL.createObjectURL(file);

    photoPreview.src = imageURL;
    photoPreview.style.display = "block";

    generateButton.disabled = false;

    statusText.textContent =
        "Photo selected successfully. Ready to generate!";
});

generateButton.addEventListener("click", function () {
    if (!selectedPhoto) {
        statusText.textContent = "Please select a photo first.";
        return;
    }

    const style = document.getElementById("styleSelect").value;

    const captions = {
        Casual: "Just enjoying the little moments ✨",
        Funny: "Proof that I occasionally look good 😂",
        Aesthetic: "Lost in the beauty of this moment 🌿",
        Romantic: "Some moments feel like a beautiful dream ❤️",
        Professional: "Capturing a moment worth remembering."
    };

    document.getElementById("caption").textContent =
        captions[style];

    document.getElementById("hashtags").textContent =
        "#SnapVoice #PhotoOfTheDay #GoodVibes #Memories";

    document.getElementById("description").textContent =
        "A photo selected by the user. The full AI photo analysis " +
        "feature will be connected in the next development stage.";

    document.getElementById("song").textContent =
        "Suggested mood: Relaxed. Suggested genre: Lo-fi.";

    statusText.textContent =
        "Demo content generated successfully!";
});

document.querySelectorAll(".copy-button").forEach(function (button) {
    button.addEventListener("click", async function () {
        const target = document.getElementById(button.dataset.target);
        const text = target.textContent;

        try {
            await navigator.clipboard.writeText(text);
            statusText.textContent = "Copied successfully!";
        } catch (error) {
            statusText.textContent =
                "Copy failed. Please select and copy the text manually.";
        }
    });
});
