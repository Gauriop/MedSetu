/* MedSetu Q&A: text + voice, English + Marathi, general-knowledge fallback,
   and clickable term chips under each answer that call /api/term-explain
   inline. Load AFTER main.js. */
(() => {
  const API =
    typeof API_BASE !== "undefined" ? API_BASE : "http://localhost:8000/api";
  const $ = (id) => document.getElementById(id);

  const T = {
    en: {
      ph: "Ask about this report, or ask anything… (press Enter, or tap 🎤 to speak)",
      wait: "Looking in your report…",
      hear: "Listening to your question…",
      listen: "🔊 Listen",
      asked: "You asked: ",
      rec: "Recording… tap 🎤 again to stop",
      err: "Could not get an answer. Is the backend running?",
      micDenied: "Microphone access is needed for voice questions.",
      noReport: "No report loaded. Please upload a report first.",
      termsLabel: "Tap a term to understand it:",
      termLoading: "Looking that up…",
    },
    mr: {
      ph: "या अहवालाबद्दल किंवा कोणताही प्रश्न विचारा… (Enter दाबा, किंवा 🎤 वर बोला)",
      wait: "तुमच्या अहवालात शोधत आहे…",
      hear: "तुमचा प्रश्न ऐकत आहे…",
      listen: "🔊 ऐका",
      asked: "तुम्ही विचारले: ",
      rec: "रेकॉर्डिंग सुरू आहे… थांबवण्यासाठी 🎤 पुन्हा दाबा",
      err: "उत्तर मिळाले नाही. बॅकएंड सुरू आहे का?",
      micDenied:
        "आवाजाने प्रश्न विचारण्यासाठी मायक्रोफोनची परवानगी आवश्यक आहे.",
      noReport: "अहवाल उपलब्ध नाही. कृपया आधी अहवाल अपलोड करा.",
      termsLabel: "समजून घेण्यासाठी संज्ञेवर टॅप करा:",
      termLoading: "शोधत आहे…",
    },
  };
  const lang = () => $("askLang").value;
  const ui = () => T[lang()];
  const reportText = () => sessionStorage.getItem("reportText") || "";

  let currentAudio = null;
  let lastSpoken = { text: "", lang: "en" };

  function applyLangUI() {
    $("askInput").placeholder = ui().ph;
    $("answerSpeak").textContent = ui().listen;
  }

  function sourceClass(source) {
    return source === "report"
      ? "src-report"
      : source === "general"
        ? "src-general"
        : "src-unavailable";
  }

  function render(data, l) {
    const box = $("answerBox"),
      out = $("answerText"),
      tr = $("askTranscript");
    box.style.display = "block";
    out.innerHTML = "";
    out.classList.toggle("mr", l === "mr");
    tr.textContent =
      data.transcript || data.question
        ? ui().asked + (data.transcript || data.question)
        : "";

    if (data.status === "unclear") {
      out.textContent = data.message;
      $("answerSpeak").style.display = "none";
      return;
    }

    if (data.source_label) {
      const badge = document.createElement("div");
      badge.className = `source-badge ${sourceClass(data.source)}`;
      badge.textContent = data.source_label;
      out.appendChild(badge);
    }

    for (const s of data.sections) {
      const row = document.createElement("div");
      row.className = "ans-row";
      const label = document.createElement("strong");
      label.textContent = s.label + ": ";
      row.append(label, document.createTextNode(s.value));
      out.appendChild(row);
    }

    if (data.terms && data.terms.length) {
      const wrap = document.createElement("div");
      wrap.className = "term-chip-wrap";
      const hint = document.createElement("div");
      hint.className = "term-chip-hint";
      hint.textContent = ui().termsLabel;
      wrap.appendChild(hint);
      data.terms.forEach((term) => wrap.appendChild(makeTermChip(term, l)));
      out.appendChild(wrap);
    }

    lastSpoken = { text: data.text, lang: l };
    $("answerSpeak").style.display = "inline-flex";
  }

  function makeTermChip(term, l) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "term-chip";
    chip.textContent = term;
    const panel = document.createElement("div");
    panel.className = "term-chip-panel";
    panel.style.display = "none";
    let loaded = false;

    chip.addEventListener("click", async () => {
      const open = panel.style.display !== "none";
      panel.style.display = open ? "none" : "block";
      if (open || loaded) return;
      panel.innerHTML = `<span class="spinner"></span> ${ui().termLoading}`;
      try {
        const res = await fetch(`${API}/term-explain`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            report_text: reportText(),
            term,
            language: l,
          }),
        });
        const data = await res.json();
        panel.innerHTML = "";
        panel.classList.toggle("mr", l === "mr");
        for (const s of data.sections) {
          const row = document.createElement("div");
          row.className = "ans-row";
          const label = document.createElement("strong");
          label.textContent = s.label + ": ";
          row.append(label, document.createTextNode(s.value));
          panel.appendChild(row);
        }
        loaded = true;
      } catch (err) {
        panel.textContent = ui().err;
      }
    });

    const holder = document.createElement("span");
    holder.className = "term-chip-holder";
    holder.append(chip, panel);
    return holder;
  }

  function stopAudio() {
    if (currentAudio) {
      currentAudio.pause();
      currentAudio = null;
    }
    if ("speechSynthesis" in window) speechSynthesis.cancel();
  }

  async function speak(text, l) {
    stopAudio();
    try {
      const res = await fetch(`${API}/tts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, language: l }),
      });
      if (!res.ok) throw new Error("tts failed");
      currentAudio = new Audio(URL.createObjectURL(await res.blob()));
      await currentAudio.play();
    } catch (e) {
      if (l === "en" && "speechSynthesis" in window) {
        const u = new SpeechSynthesisUtterance(text);
        u.lang = "en-US";
        speechSynthesis.speak(u);
      } else {
        console.warn(e);
      }
    }
  }

  function showBusy(msg) {
    $("answerBox").style.display = "block";
    $("askTranscript").textContent = "";
    $("answerSpeak").style.display = "none";
    $("answerText").innerHTML = '<span class="spinner"></span> ' + msg;
  }

  $("askInput").addEventListener("keydown", async (e) => {
    const q = e.target.value.trim();
    if (e.key !== "Enter" || !q) return;
    const l = lang();
    if (!reportText()) {
      showBusy("");
      $("answerText").textContent = ui().noReport;
      return;
    }
    showBusy(ui().wait);
    try {
      const res = await fetch(`${API}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          report_text: reportText(),
          question: q,
          language: l,
        }),
      });
      if (!res.ok) throw new Error(res.status);
      render(await res.json(), l);
    } catch (err) {
      $("answerText").textContent = ui().err;
    }
  });

  let rec = null,
    chunks = [];
  $("askMic").addEventListener("click", async () => {
    const mic = $("askMic");
    if (rec && rec.state === "recording") {
      rec.stop();
      return;
    }
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (e) {
      alert(ui().micDenied);
      return;
    }
    stopAudio();
    chunks = [];
    rec = new MediaRecorder(stream);
    rec.ondataavailable = (ev) => chunks.push(ev.data);
    rec.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      mic.classList.remove("recording");
      const type = rec.mimeType || "audio/webm";
      await sendVoice(
        new Blob(chunks, { type }),
        type.includes("ogg") ? "ogg" : type.includes("mp4") ? "mp4" : "webm",
      );
    };
    rec.start();
    mic.classList.add("recording");
    showBusy(ui().rec);
  });

  async function sendVoice(blob, ext) {
    const l = lang();
    if (!reportText()) {
      $("answerText").textContent = ui().noReport;
      return;
    }
    showBusy(ui().hear);
    const fd = new FormData();
    fd.append("audio", blob, `question.${ext}`);
    fd.append("report_text", reportText());
    fd.append("language", l);
    try {
      const res = await fetch(`${API}/voice-ask`, { method: "POST", body: fd });
      if (!res.ok) throw new Error(res.status);
      const data = await res.json();
      render(data, l);
      speak(data.text, l);
    } catch (err) {
      $("answerText").textContent = ui().err;
    }
  }

  $("answerSpeak").addEventListener("click", () =>
    speak(lastSpoken.text, lastSpoken.lang),
  );
  $("askLang").addEventListener("change", applyLangUI);
  applyLangUI();
})();
