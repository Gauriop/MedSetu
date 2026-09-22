// --- Upload page: dropzone interactions ---

const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');

if (dropzone && fileInput) {
  dropzone.addEventListener('click', () => fileInput.click());

  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('drag-over');
  });

  dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('drag-over');
  });

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('drag-over');
    if (e.dataTransfer.files.length) {
      fileInput.files = e.dataTransfer.files;
      updateDropzoneLabel(e.dataTransfer.files[0].name);
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length) {
      updateDropzoneLabel(fileInput.files[0].name);
    }
  });
}

function updateDropzoneLabel(filename) {
  const title = dropzone.querySelector('.dropzone-title');
  title.textContent = `Selected: ${filename}`;
}

// --- Backend API base URL ---
// When running the backend locally: uvicorn app:app --reload --port 8000
const API_BASE = 'http://localhost:8000/api';

// --- Report page: play buttons ---

const playEn = document.getElementById('playEn');
const playMr = document.getElementById('playMr');

if (playEn) {
  playEn.addEventListener('click', () => {
    // English playback uses the browser's built-in speech synthesis (no
    // backend TTS needed for English - gTTS is specifically for Marathi).
    speakBrowser(document.getElementById('englishSummary').textContent, 'en-US');
  });
}

if (playMr) {
  playMr.addEventListener('click', async () => {
    const marathiText = document.getElementById('marathiSummary').textContent;
    try {
      await playMarathiAudio(marathiText);
    } catch (err) {
      console.warn('Backend TTS unavailable, falling back to browser speech synthesis:', err);
      speakBrowser(marathiText, 'mr-IN');
    }
  });
}

function speakBrowser(text, lang) {
  if ('speechSynthesis' in window) {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = lang;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  } else {
    alert('Speech playback not supported in this browser.');
  }
}

async function playMarathiAudio(text) {
  const res = await fetch(`${API_BASE}/tts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error('TTS request failed');

  const audioBlob = await res.blob();
  const audioUrl = URL.createObjectURL(audioBlob);
  const audio = new Audio(audioUrl);
  audio.play();
}

// --- Ask-a-question bar (report.html) ---

const askInput = document.querySelector('.ask-bar input');

if (askInput) {
  askInput.addEventListener('keydown', async (e) => {
    if (e.key === 'Enter' && askInput.value.trim()) {
      const question = askInput.value.trim();
      const reportText = document.getElementById('englishSummary').textContent;

      try {
        const res = await fetch(`${API_BASE}/ask`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ report_text: reportText, question }),
        });
        const data = await res.json();
        alert(data.answer); // placeholder display - replace with a proper chat UI element later
      } catch (err) {
        alert('Could not reach the backend. Is it running on localhost:8000?');
      }
      askInput.value = '';
    }
  });
}
