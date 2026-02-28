// ===== State =====
const history = [];   // { scene, ok, label, conf, ms, style }
let prevBusy    = false;
let micActive   = false;
let recognition = null;
let cameraStream = null;

// Avatar state -> display mapping
const AVATAR_STATE = {
  idle:     { badge: "待机",   emoji: "🤖", speech: "等待指令...", cls: "" },
  thinking: { badge: "思考中", emoji: "🤔", speech: "让我看看...",  cls: "thinking" },
  acting:   { badge: "执行中", emoji: "🦾", speech: "动起来！",    cls: "acting" },
  done:     { badge: "完成",   emoji: "😎", speech: "搞定了！",    cls: "done" },
  error:    { badge: "出错",   emoji: "😵", speech: "出了点问题...", cls: "error" },
};

// Avatar gif mapping (drop these files in static/ to activate)
const AVATAR_GIF = {
  idle:     "/static/avatar_idle.gif",
  thinking: "/static/avatar_idle.gif",
  acting:   "/static/avatar_pick.gif",
  done:     "/static/avatar_nod.gif",
  error:    "/static/avatar_shake.gif",
};

const TILE_LABEL = {
  white_dragon: "白板 🀙",
  one_dot:      "一筒 🀇",
};

// ===== DOM helpers =====
const $ = id => document.getElementById(id);

// Update both nav-mode and play-mode avatar simultaneously
function setAvatar(stateKey, speechOverride) {
  const s   = AVATAR_STATE[stateKey] || AVATAR_STATE.idle;
  const gif = AVATAR_GIF[stateKey]   || AVATAR_GIF.idle;
  const msg = speechOverride || s.speech;

  // Nav mode
  const frame = $("avatar-frame");
  if (frame) frame.className = "avatar-frame " + s.cls;
  const emojiNav = $("avatar-emoji");
  if (emojiNav) emojiNav.textContent = s.emoji;
  const stateNav = $("avatar-state");
  if (stateNav) stateNav.textContent = s.badge;
  const speechNav = $("speech-text");
  if (speechNav) speechNav.textContent = msg;
  const imgNav = $("avatar-img-nav");
  if (imgNav) imgNav.src = gif;

  // Play mode
  const stage = $("avatar-stage");
  if (stage) stage.className = "avatar-stage " + s.cls;
  const emojiBig = $("avatar-emoji-big");
  if (emojiBig) emojiBig.textContent = s.emoji;
  const speechBig = $("speech-text-big");
  if (speechBig) speechBig.textContent = msg;
  const animImg = $("avatar-anim");
  if (animImg) animImg.src = gif;
}

function updateDot(busy, hasError) {
  const dot = $("dot");
  const lbl = $("status-label");
  if (hasError) {
    dot.className = "dot error";
    lbl.textContent = "错误";
  } else if (busy) {
    dot.className = "dot busy";
    lbl.textContent = "执行中";
  } else {
    dot.className = "dot online";
    lbl.textContent = "就绪";
  }
}

function renderRecognized(rec) {
  if (!rec) return;
  const label = TILE_LABEL[rec.label] || rec.label;
  const conf  = "置信度 " + Math.round(rec.confidence * 100) + "%";

  // Nav mode
  const recTile = $("rec-tile");
  const recConf = $("rec-conf");
  if (recTile) recTile.textContent = label;
  if (recConf) recConf.textContent = conf;

  // Play mode
  const rv = $("tile-result-value");
  const rc = $("tile-result-conf");
  if (rv) rv.textContent = label;
  if (rc) rc.textContent = conf;
}

function renderStats() {
  const total = $("stat-total");
  if (!total) return;
  total.textContent = history.length;
  if (history.length === 0) return;
  const ok = history.filter(r => r.ok).length;
  const succ = $("stat-success");
  if (succ) succ.textContent = Math.round(ok / history.length * 100) + "%";
  const avg = history.reduce((s, r) => s + r.ms, 0) / history.length;
  const avgEl = $("stat-avg");
  if (avgEl) avgEl.textContent = (avg / 1000).toFixed(1) + "s";
}

function renderHistory() {
  const tbody = $("history-body");
  if (!tbody) return;
  if (history.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="empty-row">暂无记录</td></tr>';
    return;
  }
  tbody.innerHTML = [...history].reverse().slice(0, 30).map((r, i) => {
    const n    = history.length - i;
    const ok   = r.ok ? '<span class="badge-ok">✓ 成功</span>' : '<span class="badge-fail">✗ 失败</span>';
    const sc   = `<span class="badge-${r.scene.toLowerCase()}">${r.scene}</span>`;
    const tile = r.label ? (TILE_LABEL[r.label] || r.label) : "—";
    return `<tr><td>${n}</td><td>${sc}</td><td>${ok}</td><td>${tile}</td><td>${(r.ms/1000).toFixed(2)}s</td><td>${r.style}</td></tr>`;
  }).join("");
}

function appendLog(msg) {
  // Nav mode logs
  const logsEl = $("logs");
  if (logsEl && logsEl.textContent === "—") logsEl.textContent = msg;
  else if (logsEl) logsEl.textContent += "\n" + msg;

  // Play mode log strip (newest first, 4 lines max)
  const stripEl = $("log-strip-content");
  if (stripEl) {
    const prev = stripEl.textContent === "—" ? [] : stripEl.textContent.split("\n");
    stripEl.textContent = [msg, ...prev].slice(0, 4).join("\n");
  }
}

// ===== Mode switching =====
function switchMode(mode) {
  const playScreen = $("screen-play");
  const navScreen  = $("screen-nav");
  const btnPlay    = $("btn-play");
  const btnNav     = $("btn-nav");

  if (mode === "play") {
    playScreen.classList.remove("hidden");
    navScreen.classList.add("hidden");
    btnPlay.classList.add("active");
    btnNav.classList.remove("active");
    // Sync nav → play
    const sn = $("style-nav"), fn = $("safe-nav");
    if (sn) $("style").value = sn.value;
    if (fn) $("safe").value  = fn.value;
  } else {
    navScreen.classList.remove("hidden");
    playScreen.classList.add("hidden");
    btnNav.classList.add("active");
    btnPlay.classList.remove("active");
    // Sync play → nav
    const sn = $("style-nav"), fn = $("safe-nav");
    if (sn) sn.value = $("style").value;
    if (fn) fn.value = $("safe").value;
    renderStats();
    renderHistory();
  }
}

// ===== Camera =====
async function startCamera() {
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 720 } },
    });
    const video = $("camera-feed");
    video.srcObject = cameraStream;
    const st = $("camera-status");
    st.textContent = "已连接";
    st.classList.add("on");
    appendLog("[CAM] 摄像头已连接");
  } catch (e) {
    const st = $("camera-status");
    st.textContent = "无权限";
    appendLog("[CAM] 无法访问摄像头: " + e.message);
  }
}

async function captureAndSend() {
  const video  = $("camera-feed");
  const canvas = $("camera-canvas");
  if (!cameraStream || !video || video.readyState < 2) {
    appendLog("[CAM] 摄像头未就绪，先点「开启摄像头」");
    return;
  }
  canvas.width  = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext("2d").drawImage(video, 0, 0);
  const base64 = canvas.toDataURL("image/jpeg", 0.85).split(",")[1];

  setAvatar("thinking", "正在识别牌面...");
  appendLog("[CAM] 截帧发送 OpenClaw...");

  try {
    const r = await post("/capture_frame", { image: base64 });
    if (r.recognized) {
      renderRecognized(r.recognized);
      const lbl = TILE_LABEL[r.recognized.label] || r.recognized.label;
      setAvatar("done", `识别到 ${lbl}`);
      appendLog(`[CAM] 识别完成: ${r.recognized.label} (${Math.round(r.recognized.confidence * 100)}%)`);
    } else {
      setAvatar("error", "识别失败");
      appendLog("[CAM] 识别失败: " + (r.error || "未知"));
    }
    setTimeout(() => setAvatar("idle"), 3000);
  } catch (e) {
    setAvatar("error", "网络错误");
    appendLog("[CAM] 请求失败: " + e.message);
    setTimeout(() => setAvatar("idle"), 3000);
  }
}

// ===== Voice input =====
function toggleMic() {
  micActive ? stopMic() : startMic();
}

function startMic() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    appendLog("[MIC] 浏览器不支持语音识别（请用 Chrome）");
    return;
  }
  recognition = new SR();
  recognition.lang = "zh-CN";
  recognition.continuous = false;
  recognition.interimResults = true;

  recognition.onstart = () => {
    micActive = true;
    const btn = $("mic-btn");
    if (btn) btn.classList.add("listening");
    const icon = $("mic-icon");
    if (icon) icon.textContent = "🔴";
    const lbl = $("mic-label");
    if (lbl) lbl.textContent = "录音中...";
    const tr = $("voice-transcript");
    if (tr) tr.textContent = "...";
  };

  recognition.onresult = (e) => {
    let interim = "", final = "";
    for (const r of e.results) {
      if (r.isFinal) final  += r[0].transcript;
      else           interim += r[0].transcript;
    }
    const tr = $("voice-transcript");
    if (tr) tr.textContent = final || interim || "...";
    if (final) sendVoiceCommand(final.trim());
  };

  recognition.onerror = (e) => {
    appendLog("[MIC] 识别错误: " + e.error);
    stopMic();
  };

  recognition.onend = () => stopMic();
  recognition.start();
}

function stopMic() {
  micActive = false;
  const btn  = $("mic-btn");
  const icon = $("mic-icon");
  const lbl  = $("mic-label");
  if (btn)  btn.classList.remove("listening");
  if (icon) icon.textContent = "🎤";
  if (lbl)  lbl.textContent  = "语音输入";
  if (recognition) {
    try { recognition.stop(); } catch (_) {}
    recognition = null;
  }
}

async function sendVoiceCommand(text) {
  appendLog("[VOICE] 指令: " + text);
  setAvatar("thinking", `听到了：「${text}」`);
  try {
    const r = await post("/voice_trigger", { text });
    if (r.action) appendLog("[VOICE] 执行: " + r.action);
    setAvatar("done", r.reply || "好的！");
    setTimeout(() => setAvatar("idle"), 3000);
  } catch (e) {
    setAvatar("error", "指令失败");
    appendLog("[VOICE] 请求失败: " + e.message);
    setTimeout(() => setAvatar("idle"), 2000);
  }
}

// ===== API =====
async function getStatus() {
  try {
    const res = await fetch("/status");
    if (!res.ok) throw new Error(res.status);
    const j = await res.json();

    updateDot(j.busy, !!j.last_error);

    if (j.busy && !prevBusy) {
      setAvatar("thinking");
    } else if (!j.busy && prevBusy) {
      const last = history[history.length - 1];
      if (last) {
        setAvatar(last.ok ? "done" : "error",
          last.ok ? "搞定了！" : "哎，出了点问题");
        setTimeout(() => setAvatar("idle"), 3000);
      }
    }
    prevBusy = j.busy;

    if (j.recognized) renderRecognized(j.recognized);

    // Nav logs
    const logsEl = $("logs");
    if (logsEl) logsEl.textContent = (j.logs || []).slice(-80).join("\n") || "—";

    // Play log strip
    const stripEl = $("log-strip-content");
    if (stripEl) stripEl.textContent = (j.logs || []).slice(-4).join("\n") || "—";

  } catch (e) {
    updateDot(false, true);
  }
}

async function post(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  return res.json().catch(() => ({}));
}

async function runScene(scene) {
  const style = $("style").value;
  const safe  = $("safe").value === "true";

  setAvatar("acting", scene === "A" ? "抓牌，扔出！" : "抓牌，退回！");

  $("qbtn-a").classList.remove("active");
  $("qbtn-b").classList.remove("active");
  $(`qbtn-${scene.toLowerCase()}`).classList.add("active");

  const t0 = Date.now();
  const r  = await post("/run_scene", { scene, style, safe });
  const ms = Date.now() - t0;

  $(`qbtn-${scene.toLowerCase()}`).classList.remove("active");

  if (r.recognized) renderRecognized(r.recognized);

  history.push({
    scene, ok: r.ok, ms,
    label: r.recognized?.label || null,
    conf:  r.recognized?.confidence || 0,
    style,
  });
  renderStats();
  renderHistory();

  setAvatar(r.ok ? "done" : "error",
    r.ok
      ? (scene === "A" ? "验牌完毕，扔出！" : "验牌完毕，退回！")
      : "哎，失败了...");
  setTimeout(() => setAvatar("idle"), 3000);
  await getStatus();
}

async function runExtra(action) {
  const speechMap = { tap: "点三点！", nod: "点头 ✅", shake: "摇头 ❌" };
  setAvatar("acting", speechMap[action]);
  await post(`/${action}`, {});
  setTimeout(() => setAvatar("idle"), 2000);
}

// ===== Sync selectors between modes =====
function syncSelectors() {
  const stylePlay = $("style"),     safPlay = $("safe");
  const styleNav  = $("style-nav"), safNav  = $("safe-nav");

  if (styleNav) styleNav.addEventListener("change", () => { if (stylePlay) stylePlay.value = styleNav.value; });
  if (safNav)   safNav.addEventListener("change",   () => { if (safPlay)   safPlay.value   = safNav.value; });
  if (stylePlay) stylePlay.addEventListener("change", () => { if (styleNav) styleNav.value = stylePlay.value; });
  if (safPlay)   safPlay.addEventListener("change",   () => { if (safNav)   safNav.value   = safPlay.value; });
}

// ===== Init =====
syncSelectors();
setAvatar("idle");
setInterval(getStatus, 800);
getStatus();
