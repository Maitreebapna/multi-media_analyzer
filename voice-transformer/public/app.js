const MAX_FILE_SIZE = 10 * 1024 * 1024;
const MAX_RECORDING_SECONDS = 30;
const recordTab = document.querySelector("#record-tab");
const uploadTab = document.querySelector("#upload-tab");
const recordPanel = document.querySelector("#record-panel");
const uploadPanel = document.querySelector("#upload-panel");
const recordButton = document.querySelector("#record-button");
const recordTitle = document.querySelector("#record-title");
const recordHint = document.querySelector("#record-hint");
const recordTimer = document.querySelector("#record-timer");
const audioFile = document.querySelector("#audio-file");
const uploadTitle = document.querySelector("#upload-title");
const uploadPanelHint = uploadPanel.querySelector(".panel-hint");
const preview = document.querySelector("#source-preview");
const sourceAudio = document.querySelector("#source-audio");
const transformButton = document.querySelector("#transform-button");
const voiceInput = document.querySelector("#voice-id");
const errorMessage = document.querySelector("#error-message");
const result = document.querySelector("#result");
const resultAudio = document.querySelector("#result-audio");
const downloadLink = document.querySelector("#download-link");

let selectedFile = null;
let recorder = null;
let recordingStream = null;
let timerHandle = null;
let recordingSeconds = 0;
let sourceUrl = null;
let resultUrl = null;

function showError(message) {
  errorMessage.textContent = message;
  errorMessage.hidden = !message;
}

function updateButton() {
  transformButton.disabled = !selectedFile || !voiceInput.value.trim() || transformButton.dataset.busy === "true";
}

function formatTime(seconds) {
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

function revokeUrl(url) {
  if (url) URL.revokeObjectURL(url);
}

function clearResult() {
  result.hidden = true;
  resultAudio.pause();
  resultAudio.removeAttribute("src");
  downloadLink.removeAttribute("href");
  revokeUrl(resultUrl);
  resultUrl = null;
}

function setSource(file, name = file.name || "Recorded clip") {
  if (file.size > MAX_FILE_SIZE) {
    showError("That file is over 10 MB. Choose a smaller audio file.");
    return;
  }
  selectedFile = file;
  clearResult();
  showError("");
  revokeUrl(sourceUrl);
  sourceUrl = URL.createObjectURL(file);
  sourceAudio.src = sourceUrl;
  document.querySelector("#source-file-name").textContent = name;
  document.querySelector("#source-file-meta").textContent = `${(file.size / (1024 * 1024)).toFixed(2)} MB`;
  preview.hidden = false;
  recordPanel.hidden = true;
  uploadPanel.hidden = true;
  uploadTitle.textContent = name;
  updateButton();
}

function clearSource() {
  selectedFile = null;
  audioFile.value = "";
  preview.hidden = true;
  recordPanel.hidden = recordTab.getAttribute("aria-selected") === "true" ? false : true;
  uploadPanel.hidden = uploadTab.getAttribute("aria-selected") === "true" ? false : true;
  revokeUrl(sourceUrl);
  sourceUrl = null;
  sourceAudio.removeAttribute("src");
  uploadTitle.textContent = "Drop an audio file here";
  clearResult();
  updateButton();
}

function chooseSourceTab(tab) {
  const recording = tab === recordTab;
  recordTab.classList.toggle("active", recording);
  uploadTab.classList.toggle("active", !recording);
  recordTab.setAttribute("aria-selected", String(recording));
  uploadTab.setAttribute("aria-selected", String(!recording));
  recordPanel.hidden = !recording || Boolean(selectedFile);
  uploadPanel.hidden = recording || Boolean(selectedFile);
  showError("");
}

recordTab.addEventListener("click", () => chooseSourceTab(recordTab));
uploadTab.addEventListener("click", () => chooseSourceTab(uploadTab));
voiceInput.addEventListener("input", updateButton);

audioFile.addEventListener("change", () => {
  const file = audioFile.files?.[0];
  if (!file) return;
  if (!file.type.startsWith("audio/") && !/\.(mp3|wav|m4a|ogg|webm|aac|flac)$/i.test(file.name)) {
    showError("Please choose an audio file, such as MP3, WAV, M4A, OGG, or WebM.");
    audioFile.value = "";
    return;
  }
  setSource(file);
});

for (const eventName of ["dragenter", "dragover"]) {
  uploadPanel.addEventListener(eventName, (event) => {
    event.preventDefault();
    uploadPanel.classList.add("drag-over");
  });
}
for (const eventName of ["dragleave", "drop"]) {
  uploadPanel.addEventListener(eventName, (event) => {
    event.preventDefault();
    uploadPanel.classList.remove("drag-over");
  });
}
uploadPanel.addEventListener("drop", (event) => {
  const file = event.dataTransfer?.files?.[0];
  if (file) {
    chooseSourceTab(uploadTab);
    if (file.type.startsWith("audio/") || /\.(mp3|wav|m4a|ogg|webm|aac|flac)$/i.test(file.name)) setSource(file);
    else showError("Please drop an audio file, such as MP3, WAV, M4A, OGG, or WebM.");
  }
});

function stopRecordingTracks() {
  recordingStream?.getTracks().forEach((track) => track.stop());
  recordingStream = null;
}

async function startRecording() {
  if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
    showError("Audio recording is not available in this browser. Try a recent browser or upload an audio file instead.");
    chooseSourceTab(uploadTab);
    return;
  }
  try {
    recordingStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mimeType = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg"]
      .find((type) => MediaRecorder.isTypeSupported(type));
    recorder = mimeType ? new MediaRecorder(recordingStream, { mimeType }) : new MediaRecorder(recordingStream);
    const chunks = [];
    recorder.addEventListener("dataavailable", (event) => {
      if (event.data.size) chunks.push(event.data);
    });
    recorder.addEventListener("stop", () => {
      if (chunks.length) {
        const type = recorder.mimeType || "audio/webm";
        const extension = type.includes("mp4") ? "m4a" : type.includes("ogg") ? "ogg" : "webm";
        setSource(new File(chunks, `recording.${extension}`, { type }));
        recordTitle.textContent = "Recording ready";
        recordHint.textContent = "Listen to your clip, or record another one.";
      }
      stopRecordingTracks();
    }, { once: true });
    recorder.start();
    recordingSeconds = 0;
    recordTimer.textContent = formatTime(recordingSeconds);
    recordTitle.textContent = "Recording in progress";
    recordHint.textContent = "Speak naturally. Your recording stops after 30 seconds.";
    recordButton.classList.add("recording");
    recordButton.lastElementChild.textContent = "Stop recording";
    timerHandle = setInterval(() => {
      recordingSeconds += 1;
      recordTimer.textContent = formatTime(recordingSeconds);
      if (recordingSeconds >= MAX_RECORDING_SECONDS) stopRecording();
    }, 1000);
  } catch (error) {
    stopRecordingTracks();
    showError(error.name === "NotAllowedError"
      ? "Microphone access was blocked. Allow microphone access in your browser, or upload an audio file."
      : "We couldn't start the microphone. Check your audio device or upload an audio file.");
  }
}

function stopRecording() {
  clearInterval(timerHandle);
  timerHandle = null;
  if (recorder?.state === "recording") recorder.stop();
  recordButton.classList.remove("recording");
  recordButton.lastElementChild.textContent = "Record another clip";
}

recordButton.addEventListener("click", () => {
  if (recorder?.state === "recording") stopRecording();
  else startRecording();
});
document.querySelector("#clear-source").addEventListener("click", clearSource);

transformButton.addEventListener("click", async () => {
  if (!selectedFile) return;
  transformButton.dataset.busy = "true";
  updateButton();
  transformButton.firstElementChild.textContent = "Transforming…";
  showError("");
  clearResult();
  const formData = new FormData();
  formData.append("audio", selectedFile, selectedFile.name || "recording.webm");
  formData.append("voiceId", voiceInput.value.trim());
  try {
    const response = await fetch("/api/transform", { method: "POST", body: formData });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.error || "The transformation did not finish. Please try again.");
    }
    const transformedFile = await response.blob();
    resultUrl = URL.createObjectURL(transformedFile);
    resultAudio.src = resultUrl;
    downloadLink.href = resultUrl;
    result.hidden = false;
    result.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (error) {
    showError(error instanceof TypeError
      ? "We couldn't reach the voice server. Check your connection and try again."
      : error.message);
  } finally {
    transformButton.dataset.busy = "false";
    transformButton.firstElementChild.textContent = "Transform voice";
    updateButton();
  }
});

window.addEventListener("beforeunload", () => {
  stopRecordingTracks();
  revokeUrl(sourceUrl);
  revokeUrl(resultUrl);
});
