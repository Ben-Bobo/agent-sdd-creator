// Automation SDD Builder — minimal vanilla-JS frontend.

const SESSION_KEY = "sdd_session_id";

const state = {
  sessionId: localStorage.getItem(SESSION_KEY),
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

function applyStyleButtons() {
  $$("#style-toggle button").forEach((b) =>
    b.classList.toggle("active", b.dataset.style === state.inputStyle)
  );
}

function lockSelectors(locked) {
  $$("#style-toggle button").forEach((b) => (b.disabled = locked));
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

const DOWNLOAD_ICON_SVG =
  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
  '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>' +
  '<polyline points="7 10 12 15 17 10"/>' +
  '<line x1="12" y1="15" x2="12" y2="3"/>' +
  "</svg>";

function renderArtifacts(files) {
  const container = $("#artifacts");
  container.innerHTML = "";
  for (const f of files) {
    const a = document.createElement("a");
    a.href = `/api/download/${state.sessionId}/${encodeURIComponent(f)}`;
    a.setAttribute("download", f);
    a.insertAdjacentHTML("beforeend", DOWNLOAD_ICON_SVG);
    const label = document.createElement("span");
    label.textContent = f;
    a.appendChild(label);
    container.appendChild(a);
  }
}

async function ensureSession() {
  if (state.sessionId) {
    try {
      const r = await fetch(`/api/session/${state.sessionId}`);
      if (r.ok) {
        const s = await r.json();
        state.inputStyle = s.input_style;
        setPhase(s.phase);
        setCoverage(s.coverage ? s.coverage.overall_pct : null);
        applyStyleButtons();
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
  applyStyleButtons();
  showPanels();
  setPhase("intake");
}

async function createSessionIfNeeded() {
  if (state.sessionId) return;
  const r = await fetch("/api/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ input_style: state.inputStyle }),
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
  showThinking(bodySpan, "Thinking");
  setStatus("");

  // Track whether we've started receiving real content yet.
  const chatState = { receivingContent: false };

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
        handleChatSseBlock(block, bodySpan, chatState);
      }
    }
    clearThinking(bodySpan);
  } catch (e) {
    clearThinking(bodySpan);
    setStatus("Chat failed: " + e.message);
  } finally {
    form.querySelector("button").disabled = false;
    form.message.focus();
  }
}

function showThinking(bodySpan, label) {
  bodySpan.textContent = label;
  bodySpan.classList.add("thinking");
}

function clearThinking(bodySpan) {
  bodySpan.classList.remove("thinking");
}

function handleChatSseBlock(block, bodySpan, chatState) {
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
  } else if (evType === "status") {
    if (!chatState.receivingContent)
      showThinking(bodySpan, obj.text || "Working");
  } else {
    // First content chunk: drop the thinking placeholder before appending.
    // Defensive: always clear if .thinking class is set, even if we somehow
    // missed flipping receivingContent.
    if (!chatState.receivingContent || bodySpan.classList.contains("thinking")) {
      chatState.receivingContent = true;
      clearThinking(bodySpan);
      bodySpan.textContent = "";
    }
    bodySpan.textContent += obj.text || "";
    $("#chat-transcript").scrollTop = $("#chat-transcript").scrollHeight;
  }
}

async function generate() {
  if (!state.sessionId) return;
  $("#generate-btn").disabled = true;
  setStatus("Generating — this can take 20–40 seconds…");
  const progressEl = resetGenerateProgress();
  try {
    const r = await fetch(`/api/generate/${state.sessionId}`, {
      method: "POST",
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
        handleGenerateSseBlock(block, progressEl);
      }
    }
  } catch (e) {
    setStatus("Generate failed: " + e.message);
    $("#generate-btn").disabled = false;
    markGenerateFailed(progressEl);
  }
}

function resetGenerateProgress() {
  const container = $("#generate-progress");
  container.innerHTML = "";
  container.hidden = false;
  return container;
}

function handleGenerateSseBlock(block, progressEl) {
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
  if (evType === "status") {
    markPreviousStepDone(progressEl);
    appendCurrentStep(progressEl, obj.text || "Working");
  } else if (evType === "done") {
    markPreviousStepDone(progressEl);
    renderArtifacts(obj.files || []);
    setPhase("generated");
    showPanels();
    setStatus("Done. Download the .docx on the right.");
  }
}

function markPreviousStepDone(progressEl) {
  const current = progressEl.querySelector(".gp-step.current");
  if (current) {
    current.classList.remove("current");
    current.classList.add("done");
  }
}

function appendCurrentStep(progressEl, text) {
  const step = document.createElement("div");
  step.className = "gp-step current";
  const icon = document.createElement("span");
  icon.className = "gp-icon";
  const label = document.createElement("span");
  label.className = "gp-label";
  label.textContent = text;
  step.appendChild(icon);
  step.appendChild(label);
  progressEl.appendChild(step);
}

function markGenerateFailed(progressEl) {
  const current = progressEl.querySelector(".gp-step.current");
  if (current) current.classList.replace("current", "failed");
}

function newSession() {
  if (!confirm("Discard the current session and start fresh?")) return;
  localStorage.removeItem(SESSION_KEY);
  location.reload();
}

function wireEvents() {
  $$("#style-toggle button").forEach((b) =>
    b.addEventListener("click", () => {
      if (state.sessionId) return; // locked
      state.inputStyle = b.dataset.style;
      applyStyleButtons();
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
