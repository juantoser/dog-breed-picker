const messages = document.querySelector("#messages");
const composer = document.querySelector("#composer");
const imageInput = document.querySelector("#image-input");
const messageInput = document.querySelector("#message-input");
const sendButton = document.querySelector("#send-button");
const preview = document.querySelector("#preview");
const previewImage = document.querySelector("#preview-image");
const removeImage = document.querySelector("#remove-image");

let selectedFile = null;
let selectedPreviewUrl = null;

function scrollToBottom() {
  messages.scrollTop = messages.scrollHeight;
}

function createMessage(role, content) {
  const row = document.createElement("article");
  row.className = `message-row ${role}`;

  if (role === "assistant") {
    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = "🐶";
    avatar.setAttribute("aria-hidden", "true");
    row.append(avatar);
  }

  const bubble = document.createElement("div");
  bubble.className = "bubble";

  if (typeof content === "string") {
    bubble.textContent = content;
  } else {
    bubble.append(content);
  }

  row.append(bubble);
  messages.append(row);
  scrollToBottom();
  return row;
}

function showGreeting() {
  createMessage(
    "assistant",
    "Hi! Upload a photo of yourself and I’ll suggest a dog breed match. This demo uses a deterministic stub for now."
  );
}

function showPreview(file) {
  clearPreview();
  selectedFile = file;
  selectedPreviewUrl = URL.createObjectURL(file);
  previewImage.src = selectedPreviewUrl;
  preview.hidden = false;
}

function clearPreview() {
  if (selectedPreviewUrl) {
    URL.revokeObjectURL(selectedPreviewUrl);
  }
  selectedPreviewUrl = null;
  selectedFile = null;
  imageInput.value = "";
  previewImage.removeAttribute("src");
  preview.hidden = true;
}

function renderUserMessage(text, file) {
  const content = document.createDocumentFragment();
  const message = document.createElement("div");
  message.textContent = text || "Here’s my photo.";
  content.append(message);

  if (file) {
    const image = document.createElement("img");
    image.src = URL.createObjectURL(file);
    image.alt = "Uploaded photo";
    image.onload = () => URL.revokeObjectURL(image.src);
    content.append(image);
  }

  createMessage("user", content);
}

function renderRecommendation(result) {
  const content = document.createElement("div");
  const breed = document.createElement("strong");
  breed.className = "breed";
  breed.textContent = result.breed;

  const reason = document.createElement("div");
  reason.textContent = result.reason;

  const meta = document.createElement("span");
  meta.className = "meta";
  meta.textContent = `${Math.round(result.confidence * 100)}% confidence · ${result.source}`;

  content.append(breed, reason, meta);
  createMessage("assistant", content);
}

function renderError(message) {
  const content = document.createElement("span");
  content.className = "error";
  content.textContent = message;
  createMessage("assistant", content);
}

function addTypingIndicator() {
  const indicator = document.createElement("div");
  indicator.className = "typing";
  indicator.setAttribute("aria-label", "Assistant is typing");
  indicator.innerHTML = "<span></span><span></span><span></span>";
  return createMessage("assistant", indicator);
}

function getErrorMessage(payload, fallback) {
  if (typeof payload?.detail === "string") {
    return payload.detail;
  }
  if (payload?.detail?.error) {
    return payload.detail.error;
  }
  return fallback;
}

imageInput.addEventListener("change", () => {
  const [file] = imageInput.files;
  if (!file) {
    clearPreview();
    return;
  }
  if (!file.type.startsWith("image/")) {
    renderError("Please choose an image file.");
    clearPreview();
    return;
  }
  showPreview(file);
});

removeImage.addEventListener("click", clearPreview);

composer.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!selectedFile) {
    renderError("Attach a photo first so I can make a breed match.");
    return;
  }

  const text = messageInput.value.trim();
  const fileToSend = selectedFile;
  renderUserMessage(text, fileToSend);
  clearPreview();
  messageInput.value = "";

  const typing = addTypingIndicator();
  sendButton.disabled = true;

  try {
    const formData = new FormData();
    formData.append("image", fileToSend);
    if (text) {
      formData.append("message", text);
    }

    const response = await fetch("/api/recommend", {
      method: "POST",
      body: formData,
    });
    const payload = await response.json().catch(() => ({}));
    typing.remove();

    if (!response.ok) {
      renderError(getErrorMessage(payload, "Sorry, I could not recommend a breed."));
      return;
    }

    renderRecommendation(payload);
  } catch (error) {
    typing.remove();
    renderError("Network error while getting a recommendation. Please try again.");
  } finally {
    sendButton.disabled = false;
    messageInput.focus();
  }
});

showGreeting();
