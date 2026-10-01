/* Medical Term Meaning and Translation feature.
   Requires API_BASE and $() to already be defined (see main.js). */

function initTermExplainFeature(selectors) {
  const trigger = document.createElement("button");
  trigger.id = "termTrigger";
  trigger.textContent = "Explain this";
  document.body.appendChild(trigger);

  const overlay = document.createElement("div");
  overlay.id = "termCardOverlay";
  overlay.innerHTML = `
    <div id="termCard">
      <button class="term-close" aria-label="Close">×</button>
      <h3 class="term-title" id="termTitle"></h3>
      <div class="term-tabs">
        <button class="term-tab active" data-field="simple_english">Simple English</button>
        <button class="term-tab" data-field="marathi_meaning">Marathi meaning</button>
      </div>
      <div class="term-body" id="termBody">Loading…</div>
      <div class="term-context" id="termContext" style="display:none;"></div>
      <div class="term-footer">
        <button class="term-speak" id="termSpeak">🔊 Listen in Marathi</button>
        <span class="term-disclaimer">Explains the term only — not a diagnosis.</span>
      </div>
    </div>`;
  document.body.appendChild(overlay);

  let lastResult = null;
  let selectedText = "";

  function getContextSentence(container) {
    const full = container.textContent;
    if (!selectedText) return full.slice(0, 400);
    const idx = full.indexOf(selectedText);
    if (idx === -1) return full.slice(0, 400);
    const start = Math.max(0, full.lastIndexOf(".", idx) + 1);
    const end = full.indexOf(".", idx + selectedText.length);
    return full.slice(start, end === -1 ? full.length : end + 1).trim();
  }

  function showTriggerNear(rect) {
    trigger.style.display = "block";
    trigger.style.top = `${window.scrollY + rect.top - 38}px`;
    trigger.style.left = `${window.scrollX + rect.left}px`;
  }

  function hideTrigger() {
    trigger.style.display = "none";
  }

  selectors.forEach((sel) => {
    const el = document.querySelector(sel);
    if (!el) return;
    el.addEventListener("mouseup", () => {
      const sel2 = window.getSelection();
      const text = sel2.toString().trim();
      if (!text || text.length > 80 || sel2.rangeCount === 0) {
        hideTrigger();
        return;
      }
      selectedText = text;
      const rect = sel2.getRangeAt(0).getBoundingClientRect();
      showTriggerNear(rect);
      trigger.dataset.context = getContextSentence(el);
    });
  });

  document.addEventListener("mousedown", (e) => {
    if (e.target !== trigger) hideTrigger();
  });

  trigger.addEventListener("click", async () => {
    const term = selectedText;
    const context = trigger.dataset.context || "";
    hideTrigger();
    overlay.style.display = "flex";
    $("termTitle").textContent = term;
    $("termBody").textContent = "Looking that up…";
    $("termContext").style.display = "none";
    lastResult = null;

    try {
      const res = await fetch(`${API_BASE}/term-explain`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          term,
          context,
          report_text: sessionStorage.getItem("reportText") || "",
          language: "mr",
        }),
      });
      if (!res.ok) throw new Error("request failed");
      lastResult = await res.json();
      overlay
        .querySelectorAll(".term-tab")
        .forEach((t) => t.classList.remove("active"));
      overlay
        .querySelector('.term-tab[data-field="simple_english"]')
        .classList.add("active");
      renderField("simple_english");
    } catch (err) {
      $("termBody").textContent =
        "Could not fetch an explanation. Is the backend running?";
    }
  });

  function renderField(field) {
    if (!lastResult) return;
    const body = $("termBody");
    body.textContent = lastResult[field] || "(no explanation available)";
    body.classList.toggle("mr", field === "marathi_meaning");

    const ctxBox = $("termContext");
    if (lastResult.context_note && lastResult.context_note.trim()) {
      ctxBox.style.display = "block";
      ctxBox.textContent = `In your report: ${lastResult.context_note}`;
    } else {
      ctxBox.style.display = "none";
    }
  }

  overlay.querySelectorAll(".term-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      overlay
        .querySelectorAll(".term-tab")
        .forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      renderField(tab.dataset.field);
    });
  });

  overlay.querySelector(".term-close").addEventListener("click", () => {
    overlay.style.display = "none";
  });
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) overlay.style.display = "none";
  });

  $("termSpeak").addEventListener("click", async () => {
    if (!lastResult) return;
    const text = lastResult.marathi_meaning;
    if (!text) return;
    const btn = $("termSpeak");
    btn.disabled = true;
    try {
      const res = await fetch(`${API_BASE}/tts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, language: "mr" }),
      });
      if (!res.ok) throw new Error("tts failed");
      new Audio(URL.createObjectURL(await res.blob())).play();
    } catch (err) {
      alert("Could not generate audio. Is the backend running?");
    } finally {
      btn.disabled = false;
    }
  });
}
