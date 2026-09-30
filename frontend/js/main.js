const API_BASE = "http://localhost:8000/api";

const SAMPLE_REPORT = `PREOPERATIVE DIAGNOSIS: Acute appendicitis.
POSTOPERATIVE DIAGNOSIS: Acute appendicitis with perforation.
PROCEDURE: Laparoscopic appendectomy.
The patient is a 34-year-old male who presented with right lower quadrant pain for two days. CT scan showed an inflamed appendix measuring 1.2 cm with evidence of perforation. No signs of abscess formation. The patient tolerated the procedure well and was transferred to recovery in stable condition.`;

const $ = (id) => document.getElementById(id);

async function postJSON(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${path} failed (${res.status})`);
  return res.json();
}

/* ---------------- Upload page ---------------- */

const dropzone = $("dropzone");
if (dropzone) {
  const fileInput = $("fileInput");
  const submitBtn = $("submitBtn");
  const uploadError = $("uploadError");

  dropzone.addEventListener("click", () => fileInput.click());
  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("drag-over");
  });
  dropzone.addEventListener("dragleave", () =>
    dropzone.classList.remove("drag-over"),
  );
  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("drag-over");
    if (e.dataTransfer.files.length) {
      fileInput.files = e.dataTransfer.files;
      showFile();
    }
  });
  fileInput.addEventListener("change", showFile);
  function showFile() {
    if (fileInput.files.length)
      dropzone.querySelector(".dropzone-title").textContent =
        `Selected: ${fileInput.files[0].name}`;
  }

  submitBtn.addEventListener("click", async () => {
    const text = $("reportText").value.trim();
    const file = fileInput.files[0];
    if (!file && !text) {
      uploadError.textContent = "Please upload a PDF or paste the report text.";
      uploadError.style.display = "block";
      return;
    }

    uploadError.style.display = "none";
    submitBtn.textContent = "Reading report…";
    submitBtn.disabled = true;
    try {
      const form = new FormData();
      if (file) form.append("file", file);
      else form.append("text", text);
      const res = await fetch(`${API_BASE}/ingest`, {
        method: "POST",
        body: form,
      });
      if (!res.ok) throw new Error("ingest failed");
      const data = await res.json();
      if (!data.text || data.text.length < 20)
        throw new Error("No readable text found in that file.");
      sessionStorage.setItem("reportText", data.text);
      window.location.href = "report.html";
    } catch (err) {
      uploadError.textContent = `Could not read the report: ${err.message}. Is the backend running on localhost:8000?`;
      uploadError.style.display = "block";
      submitBtn.textContent = "Summarize this report →";
      submitBtn.disabled = false;
    }
  });
}

/* ---------------- Report page ---------------- */

const DEVANAGARI_DIGITS = "०१२३४५६७८९";
const toAscii = (s) => s.replace(/[०-९]/g, (d) => DEVANAGARI_DIGITS.indexOf(d));
const MR_SIDE = {
  left: /डाव्या|डावा|डावी|डावे/,
  right: /उजव्या|उजवा|उजवी|उजवे/,
  bilateral: /दोन्ही/,
};

function cleanSummary(text) {
  return text
    .replace(/[*#`_>]/g, "")
    .replace(/^\s*[-•]\s+/gm, "")
    .replace(/\s+\n/g, "\n")
    .trim();
}
function splitSentences(text) {
  return (text.replace(/\n+/g, " ").match(/[^.!?]+[.!?]+|[^.!?]+$/g) || [text])
    .map((s) => s.trim())
    .filter(Boolean);
}
const numbersIn = (s) => toAscii(s).match(/\d+(?:\.\d+)?/g) || [];

function setStatus(msg) {
  $("statusText").textContent = msg;
}
function showError(msg) {
  const b = $("errorBox");
  b.textContent = msg;
  b.style.display = "block";
  setStatus("Something went wrong");
}

function renderTags(ex) {
  const tags = [];
  ex.measurements.forEach(([v, u]) => tags.push(`📏 ${v} ${u}`));
  ex.laterality.forEach((s) => tags.push(`↔ ${s}`));
  ex.severity.forEach((s) => tags.push(`⚠ ${s}`));
  [...new Set(ex.negations.map((n) => n.cue))].forEach((c) =>
    tags.push(`✕ "${c}"`),
  );
  $("englishTags").innerHTML = tags
    .map((t) => `<span class="tag tag-ok"></span>`)
    .join("");
  [...$("englishTags").children].forEach((el, i) => {
    el.textContent = tags[i];
  });
}

function runCheck(original, english, marathi) {
  const issues = [];
  const marNums = numbersIn(marathi);
  numbersIn(english).forEach((n) => {
    if (!marNums.includes(n))
      issues.push(`the number ${n} is missing from the Marathi text`);
  });
  Object.entries(MR_SIDE).forEach(([side, re]) => {
    if (new RegExp(`\\b${side}\\b`, "i").test(english) && !re.test(marathi))
      issues.push(`"${side}" may not be carried into Marathi`);
  });
  const box = $("checkBox");
  box.style.display = "flex";
  if (issues.length) {
    box.classList.add("warn");
    box.innerHTML = `<div><strong>Please double-check with your doctor.</strong> Automated check: ${issues.join("; ")}.</div>`;
  } else {
    box.classList.remove("warn");
    box.innerHTML =
      "<div><strong>Automated check passed.</strong> Numbers and left/right terms from the English summary appear in the Marathi text. This is a basic check, not a guarantee.</div>";
  }
}

async function loadReport() {
  const params = new URLSearchParams(window.location.search);
  const original = params.get("sample")
    ? SAMPLE_REPORT
    : sessionStorage.getItem("reportText");
  if (!original) {
    window.location.href = "upload.html";
    return;
  }
  sessionStorage.setItem("reportText", original);

  try {
    setStatus("Summarizing…");
    const s = await postJSON("/summarize", {
      report_text: original,
      use_finetuned: false,
    });
    const english = cleanSummary(s.summary);
    $("englishSummary").textContent = english;

    setStatus("Finding key details…");
    renderTags(await postJSON("/extract", { text: english }));

    setStatus("Translating to Marathi (this can take a little while)…");
    $("marathiSummary").innerHTML =
      '<span class="spinner"></span> Translating…';
    const parts = [];
    for (const sentence of splitSentences(english)) {
      parts.push(
        (await postJSON("/translate", { text: sentence })).translation,
      );
      $("marathiSummary").textContent = parts.join(" ");
    }
    const marathi = parts.join(" ");

    runCheck(original, english, marathi);
    setStatus("Done");
  } catch (err) {
    showError(
      `${err.message}. Check that the backend is running on localhost:8000 and try again.`,
    );
  }
}

if ($("englishSummary")) {
  loadReport();

  $("playEn").addEventListener("click", () => {
    if (!("speechSynthesis" in window)) return;
    const u = new SpeechSynthesisUtterance($("englishSummary").textContent);
    u.lang = "en-US";
    speechSynthesis.cancel();
    speechSynthesis.speak(u);
  });

  let currentAudio = null;

  $("playMr").addEventListener("click", async () => {
    const text = $("marathiSummary").textContent.trim();
    if (!text) return;

    // Stop and discard anything already playing before starting new audio
    if (currentAudio) {
      currentAudio.pause();
      currentAudio.currentTime = 0;
      currentAudio = null;
    }

    const btn = $("playMr");
    btn.disabled = true;
    try {
      const res = await fetch(`${API_BASE}/tts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!res.ok) throw new Error("tts failed");
      currentAudio = new Audio(URL.createObjectURL(await res.blob()));
      currentAudio.addEventListener("ended", () => {
        currentAudio = null;
      });
      await currentAudio.play();
    } catch (err) {
      showError("Could not generate Marathi audio. Is the backend running?");
    } finally {
      btn.disabled = false;
    }
  });
  $("askInput").addEventListener("keydown", async (e) => {
    const q = e.target.value.trim();
    if (e.key !== "Enter" || !q) return;
    const lang = $("askLang").value;
    const box = $("answerBox");
    const textEl = $("answerText");
    const speakBtn = $("answerSpeak");
    box.style.display = "block";
    speakBtn.style.display = "none";
    textEl.innerHTML = '<span class="spinner"></span> Looking in your report…';

    try {
      const data = await postJSON("/ask", {
        report_text: sessionStorage.getItem("reportText"),
        question: q,
        language: lang,
      });
      textEl.textContent = data.answer;
      textEl.classList.toggle("mr", lang === "mr");
      speakBtn.style.display = "inline-flex";
      speakBtn.onclick = () => speakAnswer(data.answer, lang);
    } catch (err) {
      textEl.textContent = "Could not get an answer. Is the backend running?";
    }
  });

  async function speakAnswer(text, lang) {
    if (lang === "mr") {
      try {
        const res = await fetch(`${API_BASE}/tts`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text }),
        });
        if (!res.ok) throw new Error("tts failed");
        new Audio(URL.createObjectURL(await res.blob())).play();
      } catch (err) {
        alert("Could not generate Marathi audio.");
      }
    } else {
      if (!("speechSynthesis" in window)) return;
      const u = new SpeechSynthesisUtterance(text);
      u.lang = "en-US";
      speechSynthesis.cancel();
      speechSynthesis.speak(u);
    }
  }
}
