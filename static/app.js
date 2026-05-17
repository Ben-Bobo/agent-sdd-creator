// Automation SDD Builder — minimal vanilla-JS frontend.

const SESSION_KEY = "sdd_session_id";

const state = {
  sessionId: localStorage.getItem(SESSION_KEY),
  mode: "sdd_builder",
  inputStyle: "chat",
  phase: null,
  coveragePct: null,
};

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

function setStatus(msg) {
  $("#status-msg").textContent = msg || "";
}

function setPhase(phase) {
  state.phase = phase;
  $("#phase-label").textContent = phase || "—";
}

function setCoverage(pct) {
  state.coveragePct = pct;
  if (pct === null || pct === undefined) {
    $("#coverage-pct").textContent = "—";
    $("#coverage-fill").style.width = "0%";
  } else {
    const pretty = (pct * 100).toFixed(0) + "%";
    $("#coverage-pct").textContent = pretty;
    $("#coverage-fill").style.width = pretty;
  }
  updateGenerateButton();
}

function updateGenerateButton() {
  const btn = $("#generate-btn");
  const havePhase = state.phase !== null;
  const haveSomething =
    state.coveragePct !== null && state.coveragePct > 0;
  btn.disabled = !(havePhase && haveSomething);
}

function showPanels() {
  $("#dropin-panel").hidden = state.inputStyle !== "drop_in";
  $("#chat-panel").hidden = state.inputStyle !== "chat";

  const intakeForm = $("#intake-form");
  const transcript = $("#chat-transcript");
  const chatInput = $("#chat-input");

  const inIntake = state.phase === "intake" || state.phase === null;
  intakeForm.hidden = !inIntake;
  transcript.hidden = inIntake;
  chatInput.hidden = inIntake || state.phase === "generated";
}

function applyModeStyleButtons() {
  $$("#mode-toggle button").forEach((b) =>
    b.classList.toggle("active", b.dataset.mode === state.mode)
  );
  $$("#style-toggle button").forEach((b) =>
    b.classList.toggle("active", b.dataset.style === state.inputStyle)
  );
}

function lockSelectors(locked) {
  $$("#mode-toggle button, #style-toggle button").forEach(
    (b) => (b.disabled = locked)
  );
}

function addBubble(role, text) {
  const transcript = $("#chat-transcript");
  const div = document.createElement("div");
  div.className = `chat-msg ${role}`;
  const label = document.createElement("span");
  label.className = "role-label";
  label.textContent = role === "user" ? "You" : "Assistant";
  div.appendChild(label);
  const body = document.createElement("span");
  body.className = "body";
  body.textContent = text;
  div.appendChild(body);
  transcript.appendChild(div);
  transcript.scrollTop = transcript.scrollHeight;
  return body;
}

function renderArtifacts(files) {
  const container = $("#artifacts");
  container.innerHTML = "";
  for (const f of files) {
    const a = document.createElement("a");
    a.href = `/api/download/${state.sessionId}/${encodeURIComponent(f)}`;
    a.textContent = f;
    a.setAttribute("download", f);
    container.appendChild(a);
  }
}

async function ensureSession() {
  if (state.sessionId) {
    try {
      const r = await fetch(`/api/session/${state.sessionId}`);
      if (r.ok) {
        const s = await r.json();
        state.mode = s.mode;
        state.inputStyle = s.input_style;
        setPhase(s.phase);
        setCoverage(s.coverage ? s.coverage.overall_pct : null);
        applyModeStyleButtons();
        lockSelectors(true);
        showPanels();
        for (const msg of s.transcript || []) addBubble(msg.role, msg.content);
        if (s.generated_files && s.generated_files.length)
          renderArtifacts(s.generated_files);
        return;
      }
    } catch (e) {
      // fall through to create fresh
    }
    localStorage.removeItem(SESSION_KEY);
    state.sessionId = null;
  }
  applyModeStyleButtons();
  showPanels();
  setPhase("intake");
}

async function createSessionIfNeeded() {
  if (state.sessionId) return;
  const r = await fetch("/api/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode: state.mode, input_style: state.inputStyle }),
  });
  if (!r.ok) throw new Error("Failed to create session");
  const j = await r.json();
  state.sessionId = j.session_id;
  localStorage.setItem(SESSION_KEY, j.session_id);
  lockSelectors(true);
}

async function submitIntake(ev) {
  ev.preventDefault();
  const form = ev.target;
  const intake = {
    project_name: form.project_name.value.trim(),
    business_owner: form.business_owner.value.trim() || null,
    trigger_type: form.trigger_type.value || null,
    trigger_detail: form.trigger_detail.value.trim() || null,
    frequency: form.frequency.value.trim() || null,
    applications_rough: form.applications_rough.value
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean),
    criticality: form.criticality.value || null,
  };
  setStatus("Submitting intake…");
  try {
    await createSessionIfNeeded();
    const r = await fetch("/api/intake", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: state.sessionId, intake }),
    });
    if (!r.ok) throw new Error(await r.text());
    const j = await r.json();
    setPhase(j.phase);
    if (j.opening_prompt) addBubble("assistant", j.opening_prompt);
    showPanels();
    setStatus("");
  } catch (e) {
    setStatus("Intake failed: " + e.message);
  }
}

async function submitDropin() {
  const text = $("#dropin-text").value.trim();
  const fileInput = $("#dropin-file");
  if (!text && !fileInput.files.length) {
    setStatus("Paste text or attach a file first.");
    return;
  }
  setStatus("Extracting…");
  $("#dropin-submit").disabled = true;
  try {
    await createSessionIfNeeded();
    const fd = new FormData();
    fd.append("session_id", state.sessionId);
    if (text) fd.append("raw_text", text);
    if (fileInput.files[0]) fd.append("file", fileInput.files[0]);
    const r = await fetch("/api/dropin", { method: "POST", body: fd });
    if (!r.ok) throw new Error(await r.text());
    setStatus("Running gap analysis…");
    const cr = await fetch(`/api/coverage/${state.sessionId}`, {
      method: "POST",
    });
    if (!cr.ok) throw new Error(await cr.text());
    const cov = await cr.json();
    setCoverage(cov.overall_pct);
    setPhase("ready_to_generate");
    setStatus("");
  } catch (e) {
    setStatus("Drop-in failed: " + e.message);
  } finally {
    $("#dropin-submit").disabled = false;
  }
}

async function sendChat(ev) {
  ev.preventDefault();
  const form = ev.target;
  const message = form.message.value.trim();
  if (!message) return;
  form.message.value = "";
  form.querySelector("button").disabled = true;
  addBubble("user", message);
  const bodySpan = addBubble("assistant", "");
  setStatus("Thinking…");

  try {
    const r = await fetch(`/api/chat/${state.sessionId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    if (!r.ok) throw new Error(await r.text());

    const reader = r.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let idx;
      while ((idx = buffer.indexOf("\n\n")) >= 0) {
        const block = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        handleSseBlock(block, bodySpan);
      }
    }
    setStatus("");
  } catch (e) {
    setStatus("Chat failed: " + e.message);
  } finally {
    form.querySelector("button").disabled = false;
    form.message.focus();
  }
}

function handleSseBlock(block, bodySpan) {
  let evType = null;
  let dataLine = null;
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) evType = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLine = line.slice(5).trim();
  }
  if (dataLine === null) return;
  let obj;
  try {
    obj = JSON.parse(dataLine);
  } catch (_) {
    return;
  }
  if (evType === "done") {
    setPhase(obj.phase);
    if (obj.coverage_pct !== null && obj.coverage_pct !== undefined)
      setCoverage(obj.coverage_pct);
    showPanels();
  } else {
    bodySpan.textContent += obj.text || "";
    $("#chat-transcript").scrollTop = $("#chat-transcript").scrollHeight;
  }
}

async function generate() {
  if (!state.sessionId) return;
  $("#generate-btn").disabled = true;
  setStatus("Generating — this can take 20–40 seconds…");
  try {
    const r = await fetch(`/api/generate/${state.sessionId}`, {
      method: "POST",
    });
    if (!r.ok) throw new Error(await r.text());
    const j = await r.json();
    renderArtifacts(j.files);
    setPhase("generated");
    showPanels();
    setStatus("Done. Download the artifacts on the right.");
  } catch (e) {
    setStatus("Generate failed: " + e.message);
    $("#generate-btn").disabled = false;
  }
}

function newSession() {
  if (!confirm("Discard the current session and start fresh?")) return;
  localStorage.removeItem(SESSION_KEY);
  location.reload();
}

function wireEvents() {
  $$("#mode-toggle button").forEach((b) =>
    b.addEventListener("click", () => {
      if (state.sessionId) return; // locked
      state.mode = b.dataset.mode;
      applyModeStyleButtons();
      // Technology Fit mode is drop-in only (no chat for v1).
      if (state.mode === "technology_fit") {
        state.inputStyle = "drop_in";
        applyModeStyleButtons();
        showPanels();
      }
    })
  );
  $$("#style-toggle button").forEach((b) =>
    b.addEventListener("click", () => {
      if (state.sessionId) return; // locked
      state.inputStyle = b.dataset.style;
      applyModeStyleButtons();
      showPanels();
    })
  );

  $("#intake-form").addEventListener("submit", submitIntake);
  $("#dropin-submit").addEventListener("click", submitDropin);
  $("#chat-input").addEventListener("submit", sendChat);
  $("#generate-btn").addEventListener("click", generate);
  $("#new-session-btn").addEventListener("click", newSession);

  // Ctrl/Cmd+Enter in chat textarea submits.
  $("#chat-input textarea").addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      $("#chat-input").requestSubmit();
    }
  });
}

(async function init() {
  wireEvents();
  await ensureSession();
})();
