/* ==========================================================================
   Roshtaty â€” frontend logic
   ========================================================================== */

const API_BASE = "";
const SAMPLES = ["assets/sample-prescription.png", "assets/sample-prescription-2.png"];
const HISTORY_KEY = "Roshtaty.history.v1";
const HISTORY_LIMIT = 6;
const MAX_UPLOAD_MB = 10;
const ALLOWED_TYPES = /^image\/(png|jpe?g|webp|bmp|tiff)$/i;

const elements = {
    dropzone: document.getElementById("dropzone"),
    imageInput: document.getElementById("imageInput"),
    preview: document.getElementById("preview"),
    previewImage: document.getElementById("previewImage"),
    fileName: document.getElementById("fileName"),
    fileSize: document.getElementById("fileSize"),
    removeFile: document.getElementById("removeFile"),
    extractButton: document.getElementById("extractButton"),
    sampleButton: document.getElementById("sampleButton"),
    resultsPanel: document.getElementById("resultsPanel"),
    resultsEmpty: document.getElementById("resultsEmpty"),
    resultsLoading: document.getElementById("resultsLoading"),
    resultsContent: document.getElementById("resultsContent"),
    resultMeta: document.getElementById("resultMeta"),
    statRow: document.getElementById("statRow"),
    medicineList: document.getElementById("medicineList"),
    rawText: document.getElementById("rawText"),
    rawMeta: document.getElementById("rawMeta"),
    statusPill: document.getElementById("statusPill"),
    statusText: document.getElementById("statusText"),
    copyButton: document.getElementById("copyButton"),
    downloadTxt: document.getElementById("downloadTxt"),
    downloadCsv: document.getElementById("downloadCsv"),
    newScanButton: document.getElementById("newScanButton"),
    headerNewScan: document.getElementById("headerNewScan"),
    history: document.getElementById("history"),
    historyGrid: document.getElementById("historyGrid"),
    clearHistory: document.getElementById("clearHistory"),
    toast: document.getElementById("toast"),
};

const state = {
    file: null,
    previewUrl: null,
    result: null,
    busy: false,
    fromHistory: false,
    toastTimer: null,
    requestId: 0,
};

/* --------------------------------------------------------------------------
   Helpers
   -------------------------------------------------------------------------- */

function escapeHtml(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function formatBytes(bytes) {
    if (!bytes) return "0 KB";
    if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function setStatus(stateName, label) {
    elements.statusPill.dataset.state = stateName;
    elements.statusText.textContent = label;
}

function showToast(message, isError = false) {
    const toast = elements.toast;
    toast.textContent = message;
    toast.classList.toggle("is-error", isError);
    toast.classList.add("is-visible");

    clearTimeout(state.toastTimer);
    state.toastTimer = setTimeout(() => toast.classList.remove("is-visible"), 2600);
}

function downloadFile(name, content, type) {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = name;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1500);
}

function safeFileName(result, extension) {
    const patient = result?.patient?.name || "";
    const base = (patient || "prescription")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "")
        .slice(0, 40);

    const date = new Date().toISOString().slice(0, 10);
    return `Roshtaty-${base || "prescription"}-${date}.${extension}`;
}

/* --------------------------------------------------------------------------
   File selection
   -------------------------------------------------------------------------- */

function validateFile(file) {
    if (!file) return "Choose an image first.";
    if (!ALLOWED_TYPES.test(file.type || "")) {
        return "Unsupported file type. Use JPG, PNG, WEBP, BMP or TIFF.";
    }
    if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
        return `That image is ${formatBytes(file.size)}. The limit is ${MAX_UPLOAD_MB} MB.`;
    }
    return "";
}

function setFile(file) {
    const error = validateFile(file);

    if (error) {
        showToast(error, true);
        return false;
    }

    if (state.previewUrl) URL.revokeObjectURL(state.previewUrl);

    state.file = file;
    state.previewUrl = URL.createObjectURL(file);
    state.fromHistory = false;

    elements.previewImage.src = state.previewUrl;
    elements.fileName.textContent = file.name;
    elements.fileSize.textContent = formatBytes(file.size);
    elements.preview.hidden = false;
    elements.dropzone.hidden = true;
    elements.extractButton.disabled = false;

    state.result = null;
    showEmpty();
    setStatus("idle", "Ready to scan");
    return true;
}

function clearFile({ keepResult = false } = {}) {
    if (state.previewUrl) URL.revokeObjectURL(state.previewUrl);

    state.file = null;
    state.previewUrl = null;
    state.fromHistory = false;
    state.requestId += 1;

    elements.imageInput.value = "";
    elements.preview.hidden = true;
    elements.previewImage.removeAttribute("src");
    elements.dropzone.hidden = false;
    elements.extractButton.disabled = true;
    elements.resultsPanel.setAttribute("aria-busy", "false");

    if (!keepResult) {
        state.result = null;
        showEmpty();
        setStatus("idle", "Waiting for image");
    }
}

/* --------------------------------------------------------------------------
   Results rendering
   -------------------------------------------------------------------------- */

function showEmpty() {
    elements.resultsEmpty.hidden = false;
    elements.resultsLoading.hidden = true;
    elements.resultsContent.hidden = true;
}

function showLoading() {
    elements.resultsEmpty.hidden = true;
    elements.resultsLoading.hidden = false;
    elements.resultsContent.hidden = true;
}

function showResults() {
    elements.resultsEmpty.hidden = true;
    elements.resultsLoading.hidden = true;
    elements.resultsContent.hidden = false;
}

function showError(message) {
    elements.resultsEmpty.hidden = true;
    elements.resultsLoading.hidden = true;
    elements.resultsContent.hidden = false;
    elements.resultsContent.dataset.state = "error";

    elements.resultMeta.innerHTML = "";
    elements.statRow.innerHTML = "";
    elements.rawText.textContent = "";
    elements.rawMeta.textContent = "";
    resultActionsState(false);

    elements.medicineList.innerHTML = `
        <div class="medicine-empty" style="padding:30px 20px;">
            <strong style="display:block;color:#b42318;font-size:14px;margin-bottom:6px;">We could not read this image</strong>
            <span>${escapeHtml(message)}</span>
            <div style="margin-top:16px;">
                <button class="button button-small button-secondary" id="retryButton" type="button">Try again</button>
            </div>
        </div>
    `;

    const retry = document.getElementById("retryButton");
    if (retry) retry.addEventListener("click", runExtraction);
}

function resultActionsState(enabled) {
    [elements.copyButton, elements.downloadTxt, elements.downloadCsv].forEach((button) => {
        button.disabled = !enabled;
    });
}

function metaChip(icon, label, value) {
    return `
        <span class="meta-chip">
            ${icon}
            <span>${escapeHtml(label)}</span>
            <strong>${escapeHtml(value)}</strong>
        </span>
    `;
}

const ICON_PATIENT = `<svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="10" cy="6.5" r="3.2" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M3.8 17c.5-3.2 3-5.2 6.2-5.2s5.7 2 6.2 5.2" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>`;
const ICON_CALENDAR = `<svg viewBox="0 0 20 20" aria-hidden="true"><rect x="3" y="4.5" width="14" height="12.5" rx="2" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M3 8.5h14M7 2.8v3.4M13 2.8v3.4" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>`;
const ICON_DOCTOR = `<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 2.5v4M8 6.5h4M6 9h8v3.5a4 4 0 0 1-8 0V9Z" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
const ICON_FILE = `<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M5.5 2.8h6L15 6.3v10.9h-9.5z" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/><path d="M11.5 2.8v3.5H15" fill="none" stroke="currentColor" stroke-width="1.4"/></svg>`;

function renderResult(result) {
    state.result = result;
    elements.resultsContent.dataset.state = "ok";

    const patient = result.patient || {};
    const medicines = Array.isArray(result.medicines) ? result.medicines : [];

    /* Meta chips */
    const chips = [];
    if (patient.name) chips.push(metaChip(ICON_PATIENT, "Patient", patient.name));
    if (patient.date) chips.push(metaChip(ICON_CALENDAR, "Date", patient.date));
    if (patient.doctor) chips.push(metaChip(ICON_DOCTOR, "Doctor", patient.doctor));
    if (result.filename) chips.push(metaChip(ICON_FILE, "Source", result.filename));
    elements.resultMeta.innerHTML = chips.join("");

    /* Stats */
    const seconds = Math.max(0.1, (result.processing_ms || 0) / 1000).toFixed(1);
    elements.statRow.innerHTML = `
        <div class="stat">
            <span class="stat-value">${Math.round(result.confidence || 0)}%</span>
            <span class="stat-label">OCR confidence</span>
        </div>
        <div class="stat">
            <span class="stat-value">${medicines.length}</span>
            <span class="stat-label">${medicines.length === 1 ? "Medicine found" : "Medicines found"}</span>
        </div>
        <div class="stat">
            <span class="stat-value">${seconds}s</span>
            <span class="stat-label">Processing time</span>
        </div>
    `;

    /* Medicines */
    if (!medicines.length) {
        elements.medicineList.innerHTML = `
            <div class="medicine-empty">
                Text was read, but no medicine details were recognised.
                Open the raw text below to review the scan.
            </div>
        `;
    } else {
        elements.medicineList.innerHTML = medicines.map((medicine, index) => {
            const details = [
                ["Dose", medicine.dose],
                ["Frequency", medicine.frequency],
                ["Duration", medicine.duration],
            ]
                .map(
                    ([label, value]) => `
                        <div>
                            <span>${label}</span>
                            <strong class="${value ? "" : "is-muted"}">${escapeHtml(value || "\u2014")}</strong>
                        </div>
                    `
                )
                .join("");

            const badge = medicine.form
                ? `<span class="med-form-badge">${escapeHtml(medicine.form)}</span>`
                : medicine.duration
                    ? `<span class="med-duration">${escapeHtml(medicine.duration)}</span>`
                    : "";

            const note = medicine.instructions
                ? `<p class="med-note">
                        <svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6.5" fill="none" stroke="currentColor" stroke-width="1.2"/><path d="M8 7.2v3.4M8 4.9v.1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
                        ${escapeHtml(medicine.instructions)}
                   </p>`
                : "";

            return `
                <article class="medicine">
                    <div class="med-top">
                        <span class="med-index">${index + 1}</span>
                        <div class="med-name">
                            <h3>
                                ${escapeHtml(medicine.name || "Unnamed medicine")}
                                ${medicine.strength ? `<span class="med-strength">${escapeHtml(medicine.strength)}</span>` : ""}
                            </h3>
                        </div>
                        ${badge}
                    </div>
                    ${details ? `<div class="med-grid">${details}</div>` : ""}
                    ${note}
                </article>
            `;
        }).join("");
    }

    /* Raw text */
    elements.rawText.textContent = result.raw_text || "";
    elements.rawMeta.textContent = result.word_count ? `${result.word_count} words read` : "";

    resultActionsState(true);
    showResults();
}

/* --------------------------------------------------------------------------
   API
   -------------------------------------------------------------------------- */

async function runExtraction() {
    if (state.busy) return;

    if (!state.file) {
        if (state.fromHistory) {
            showToast("This is a saved scan. Choose a new image to scan again.", true);
            return;
        }
        showToast("Choose a prescription image first.", true);
        return;
    }

    state.busy = true;
    const requestId = ++state.requestId;

    elements.extractButton.disabled = true;
    elements.resultsPanel.setAttribute("aria-busy", "true");
    setStatus("working", "Readingâ€¦");
    showLoading();

    try {
        const formData = new FormData();
        formData.append("image", state.file);

        const response = await fetch(`${API_BASE}/extract-text`, {
            method: "POST",
            body: formData,
        });

        let data = null;
        try {
            data = await response.json();
        } catch {
            data = null;
        }

        // A newer scan (or a reset) superseded this request.
        if (requestId !== state.requestId) return;

        if (!response.ok || !data || !data.success) {
            throw new Error(
                data && data.error
                    ? data.error
                    : `The server returned an error (${response.status}).`
            );
        }

        renderResult(data);
        setStatus("done", "Completed");
        saveToHistory(data);
        showToast(`Prescription read â€” ${data.medicines.length} medicine${data.medicines.length === 1 ? "" : "s"} found.`);
    } catch (error) {
        if (requestId !== state.requestId) return;

        console.error(error);
        setStatus("error", "Not recognized");
        showError(error.message || "Could not reach the OCR server.");
        showToast("Extraction failed. Please try again.", true);
    } finally {
        state.busy = false;

        if (requestId === state.requestId) {
            elements.extractButton.disabled = !state.file;
            elements.resultsPanel.setAttribute("aria-busy", "false");
        }
    }
}

/* --------------------------------------------------------------------------
   History
   -------------------------------------------------------------------------- */

function readHistory() {
    try {
        const raw = localStorage.getItem(HISTORY_KEY);
        const parsed = raw ? JSON.parse(raw) : [];
        return Array.isArray(parsed) ? parsed : [];
    } catch {
        return [];
    }
}

function writeHistory(entries) {
    try {
        localStorage.setItem(HISTORY_KEY, JSON.stringify(entries));
    } catch {
        /* Storage may be full or disabled â€” history is a nice-to-have. */
    }
}

function makeThumbnail(file) {
    return new Promise((resolve) => {
        const image = new Image();
        const url = URL.createObjectURL(file);

        image.onload = () => {
            const width = 320;
            const height = Math.round((image.height / image.width) * width);
            const canvas = document.createElement("canvas");
            canvas.width = width;
            canvas.height = height;

            canvas.getContext("2d").drawImage(image, 0, 0, width, height);
            URL.revokeObjectURL(url);

            try {
                resolve(canvas.toDataURL("image/jpeg", 0.72));
            } catch {
                resolve("");
            }
        };

        image.onerror = () => {
            URL.revokeObjectURL(url);
            resolve("");
        };

        image.src = url;
    });
}

async function saveToHistory(result) {
    const thumbnail = state.file ? await makeThumbnail(state.file) : "";

    const entry = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        createdAt: Date.now(),
        filename: result.filename || state.file?.name || "prescription",
        thumbnail,
        patient: result.patient || {},
        raw_text: result.raw_text || "",
        confidence: result.confidence || 0,
        word_count: result.word_count || 0,
        processing_ms: result.processing_ms || 0,
        medicines: result.medicines || [],
    };

    const entries = [entry, ...readHistory()].slice(0, HISTORY_LIMIT);
    writeHistory(entries);
    renderHistory(entries);
}

function relativeTime(timestamp) {
    const diff = Date.now() - timestamp;
    const minutes = Math.round(diff / 60000);

    if (minutes < 1) return "Just now";
    if (minutes < 60) return `${minutes} min ago`;

    const hours = Math.round(minutes / 60);
    if (hours < 24) return `${hours} h ago`;

    return new Date(timestamp).toLocaleDateString(undefined, {
        day: "2-digit",
        month: "short",
    });
}

function renderHistory(entries = readHistory()) {
    if (!entries.length) {
        elements.history.hidden = true;
        elements.historyGrid.innerHTML = "";
        return;
    }

    elements.history.hidden = false;
    elements.historyGrid.innerHTML = entries
        .map((entry) => {
            const title = entry.patient?.name || entry.filename || "Prescription";
            const meta = entry.patient?.date
                ? `${entry.patient.date} Â· ${relativeTime(entry.createdAt)}`
                : relativeTime(entry.createdAt);
            const count = entry.medicines?.length || 0;

            return `
                <div class="history-card" role="button" tabindex="0" data-entry-id="${escapeHtml(entry.id)}" aria-label="Open saved scan for ${escapeHtml(title)}">
                    <span class="history-thumb">
                        ${entry.thumbnail ? `<img src="${entry.thumbnail}" alt="">` : ""}
                    </span>
                    <span class="history-body">
                        <span class="history-title">${escapeHtml(title)}</span>
                        <span class="history-sub">${escapeHtml(meta)}</span>
                        <span class="history-tags">
                            <span class="history-tag">${count} ${count === 1 ? "medicine" : "medicines"}</span>
                            <span class="history-tag">${Math.round(entry.confidence)}%</span>
                        </span>
                    </span>
                </div>
            `;
        })
        .join("");

    elements.historyGrid.querySelectorAll("[data-entry-id]").forEach((card) => {
        const open = () => restoreHistory(card.dataset.entryId);

        card.addEventListener("click", open);
        card.addEventListener("keydown", (event) => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                open();
            }
        });
    });
}

function restoreHistory(id) {
    if (state.busy) return;

    const entry = readHistory().find((item) => item.id === id);
    if (!entry) return;

    state.file = null;
    state.fromHistory = true;

    if (state.previewUrl) URL.revokeObjectURL(state.previewUrl);
    state.previewUrl = null;

    if (entry.thumbnail) {
        elements.previewImage.src = entry.thumbnail;
        elements.fileName.textContent = entry.filename;
        elements.fileSize.textContent = "Saved scan";
        elements.preview.hidden = false;
        elements.dropzone.hidden = true;
    } else {
        elements.preview.hidden = true;
        elements.dropzone.hidden = false;
    }

    elements.extractButton.disabled = true;

    renderResult(entry);
    setStatus("done", "Saved scan");

    document.querySelector(".workspace").scrollIntoView({ behavior: "smooth", block: "start" });
}

/* --------------------------------------------------------------------------
   Sample prescriptions
   -------------------------------------------------------------------------- */

async function loadSample(index = 0) {
    if (state.busy) return;

    elements.sampleButton.disabled = true;
    setStatus("working", "Loading sampleâ€¦");

    try {
        const response = await fetch(SAMPLES[index % SAMPLES.length]);
        if (!response.ok) throw new Error("Sample image could not be loaded.");

        const blob = await response.blob();
        const name = SAMPLES[index % SAMPLES.length].split("/").pop();

        const file = new File([blob], name, { type: "image/png" });

        if (!setFile(file)) return;

        await runExtraction();
    } catch (error) {
        console.error(error);
        setStatus("error", "Sample failed");
        showError(error.message || "Could not load the sample image.");
    } finally {
        elements.sampleButton.disabled = false;
    }
}

/* --------------------------------------------------------------------------
   Copy / download
   -------------------------------------------------------------------------- */

function buildTextReport(result) {
    const patient = result.patient || {};
    const lines = ["Roshtaty â€” Prescription summary", "=".repeat(32)];

    if (patient.name) lines.push(`Patient: ${patient.name}`);
    if (patient.age) lines.push(`Age: ${patient.age}`);
    if (patient.date) lines.push(`Date: ${patient.date}`);
    if (patient.doctor) lines.push(`Doctor: ${patient.doctor}`);
    if (patient.name || patient.age || patient.date || patient.doctor) lines.push("");

    (result.medicines || []).forEach((medicine, index) => {
        lines.push(`${index + 1}. ${medicine.name}${medicine.strength ? ` ${medicine.strength}` : ""}${medicine.form ? ` (${medicine.form})` : ""}`);
        if (medicine.dose) lines.push(`   Dose: ${medicine.dose}`);
        if (medicine.frequency) lines.push(`   Frequency: ${medicine.frequency}`);
        if (medicine.duration) lines.push(`   Duration: ${medicine.duration}`);
        if (medicine.instructions) lines.push(`   Notes: ${medicine.instructions}`);
        lines.push("");
    });

    if (result.raw_text) {
        lines.push("-".repeat(32), "Raw OCR text", "-".repeat(32), result.raw_text);
    }

    return lines.join("\n");
}

function buildCsv(result) {
    const escapeCell = (value) => `"${String(value ?? "").replace(/"/g, '""')}"`;
    const rows = [["Medicine", "Strength", "Form", "Dose", "Frequency", "Duration", "Instructions"]];

    (result.medicines || []).forEach((medicine) => {
        rows.push([
            medicine.name,
            medicine.strength,
            medicine.form,
            medicine.dose,
            medicine.frequency,
            medicine.duration,
            medicine.instructions,
        ]);
    });

    return rows.map((row) => row.map(escapeCell).join(",")).join("\r\n");
}

async function copyReport() {
    if (!state.result) return;

    const text = buildTextReport(state.result);

    try {
        await navigator.clipboard.writeText(text);
        showToast("Summary copied to clipboard.");
    } catch {
        const area = document.createElement("textarea");
        area.value = text;
        area.style.position = "fixed";
        area.style.opacity = "0";
        document.body.appendChild(area);
        area.select();

        const copied = document.execCommand("copy");
        area.remove();

        showToast(copied ? "Summary copied to clipboard." : "Copy failed â€” use the download buttons.", !copied);
    }
}

/* --------------------------------------------------------------------------
   Wiring
   -------------------------------------------------------------------------- */

elements.dropzone.addEventListener("click", () => elements.imageInput.click());

elements.dropzone.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        elements.imageInput.click();
    }
});

elements.imageInput.addEventListener("change", () => {
    const file = elements.imageInput.files[0];
    if (file) setFile(file);
});

["dragenter", "dragover"].forEach((type) => {
    elements.dropzone.addEventListener(type, (event) => {
        event.preventDefault();
        elements.dropzone.classList.add("is-dragging");
    });
});

["dragleave", "drop"].forEach((type) => {
    elements.dropzone.addEventListener(type, (event) => {
        event.preventDefault();
        elements.dropzone.classList.remove("is-dragging");
    });
});

elements.dropzone.addEventListener("drop", (event) => {
    const file = event.dataTransfer.files[0];
    if (file) setFile(file);
});

elements.removeFile.addEventListener("click", () => clearFile());

elements.extractButton.addEventListener("click", runExtraction);

elements.sampleButton.addEventListener("click", () => loadSample(0));

elements.copyButton.addEventListener("click", copyReport);

elements.downloadTxt.addEventListener("click", () => {
    if (!state.result) return;
    downloadFile(safeFileName(state.result, "txt"), buildTextReport(state.result), "text/plain;charset=utf-8");
    showToast(".txt report downloaded.");
});

elements.downloadCsv.addEventListener("click", () => {
    if (!state.result) return;
    downloadFile(safeFileName(state.result, "csv"), buildCsv(state.result), "text/csv;charset=utf-8");
    showToast(".csv spreadsheet downloaded.");
});

function resetToNewScan() {
    clearFile();
    document.querySelector(".workspace").scrollIntoView({ behavior: "smooth", block: "start" });
    window.setTimeout(() => elements.dropzone.focus({ preventScroll: true }), 350);
}

elements.newScanButton.addEventListener("click", resetToNewScan);
elements.headerNewScan.addEventListener("click", resetToNewScan);

elements.clearHistory.addEventListener("click", () => {
    writeHistory([]);
    renderHistory([]);
    showToast("Scan history cleared.");
});

/* --------------------------------------------------------------------------
   Startup
   -------------------------------------------------------------------------- */

renderHistory();

const params = new URLSearchParams(window.location.search);
const demoParam = params.get("demo");
const sampleParam = params.get("sample");

if (demoParam !== null || sampleParam !== null) {
    const index = Number.parseInt(sampleParam || "0", 10) || 0;
    window.setTimeout(() => loadSample(index), 250);
}


/* --------------------------------------------------------------------------
   Welcome notice (shown before the home page)
   -------------------------------------------------------------------------- */

(function initWelcome() {
    const overlay = document.getElementById("welcomeOverlay");
    const button = document.getElementById("welcomeContinue");
    if (!overlay || !button) return;

    // Shown once per browser session. To show it on every page load,
    // set SHOW_EVERY_TIME to true.
    const SHOW_EVERY_TIME = false;
    const SEEN_KEY = "Roshtaty.welcomeSeen.v1";

    const closeNow = () => {
        overlay.remove();
        document.body.style.overflow = "";
    };

    if (!SHOW_EVERY_TIME) {
        try {
            if (sessionStorage.getItem(SEEN_KEY)) {
                closeNow();
                return;
            }
        } catch (error) { /* storage unavailable: just show the notice */ }
    }

    document.body.style.overflow = "hidden";
    button.focus({ preventScroll: true });

    button.addEventListener("click", () => {
        try { sessionStorage.setItem(SEEN_KEY, "1"); } catch (error) { /* ignore */ }
        overlay.classList.add("is-hiding");
        document.body.style.overflow = "";
        window.setTimeout(closeNow, 300);
    });
})();
