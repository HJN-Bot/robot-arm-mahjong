// ===== State =====
const history = [];   // { scene, ok, label, conf, ms, style }
let prevBusy    = false;
let micActive   = false;
let recognition = null;
let cameraStream = null;

// Auto-recognition loop
const AUTO_CONF_THRESHOLD = 0.0;    // 不设置置信度门槛，识别到什么就输出什么
const AUTO_INTERVAL_MS    = 1500;   // capture every 1.5s
const AUTO_COOLDOWN_MS    = 7000;   // pause 7s after triggering scene
let autoLoopActive   = false;
let autoLoopCooldown = false;
let autoLoopTimer    = null;
let countdownTimer   = null;  // 3s auto-trigger countdown after camera open

// Avatar state -> display mapping
const AVATAR_STATE = {
  idle:     { badge: "待机",   emoji: "🤖", speech: "等待指令...", cls: "" },
  thinking: { badge: "思考中", emoji: "🤔", speech: "让我看看...",  cls: "thinking" },
  acting:   { badge: "执行中", emoji: "🦾", speech: "动起来！",    cls: "acting" },
  done:     { badge: "完成",   emoji: "😎", speech: "搞定了！",    cls: "done" },
  error:    { badge: "出错",   emoji: "😵", speech: "出了点问题...", cls: "error" },
};

// Avatar gif mapping — omit a key to fall back to emoji for that state
const AVATAR_GIF = {
  // idle / thinking: 暂用 emoji，等高清 GIF 素材到位后再填入
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

// Stop all scene videos and restore the emoji circle
function hideAllAvatarVideos() {
  ["avatar-video-scene-a", "avatar-video-scene-b"].forEach(id => {
    const v = $(id);
    if (!v) return;
    try { v.pause(); } catch (_) {}
    v.style.display = "none";
  });
  // Restore emoji circle
  const stage = $("avatar-stage");
  if (stage) stage.style.display = "";
}

// Play the scene video for A or B — hides the circle, shows full-frame video
function playSceneVideo(scene) {
  const id = scene === "A" ? "avatar-video-scene-a" : "avatar-video-scene-b";
  const v = $(id);
  if (!v) return;
  // Stop any other playing video (don't call hideAllAvatarVideos to avoid restoring stage)
  ["avatar-video-scene-a", "avatar-video-scene-b"].forEach(otherId => {
    if (otherId === id) return;
    const other = $(otherId);
    if (other) { try { other.pause(); } catch (_) {} other.style.display = "none"; }
  });
  // Hide the circle stage, show full-frame video
  const stage = $("avatar-stage");
  if (stage) stage.style.display = "none";
  v.style.display = "block";
  try { v.currentTime = 0; } catch (_) {}
  const p = v.play();
  if (p && typeof p.catch === "function") {
    p.catch(err => appendLog("[VIDEO] Scene" + scene + " 播放失败: " + err.message));
  }
}

// Update both nav-mode and play-mode avatar simultaneously
function setAvatar(stateKey, speechOverride) {
  // Stop any playing scene video before updating avatar state
  hideAllAvatarVideos();

  const s   = AVATAR_STATE[stateKey] || AVATAR_STATE.idle;
  const gif = AVATAR_GIF[stateKey];   // undefined → show emoji instead
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
  if (imgNav) { imgNav.style.display = gif ? "" : "none"; if (gif) imgNav.src = gif; }

  // Play mode
  const stage = $("avatar-stage");
  if (stage) stage.className = "avatar-stage " + s.cls;
  const emojiBig = $("avatar-emoji-big");
  if (emojiBig) emojiBig.textContent = s.emoji;
  const speechBig = $("speech-text-big");
  if (speechBig) speechBig.textContent = msg;
  const animImg = $("avatar-anim");
  if (animImg) { animImg.style.display = gif ? "" : "none"; if (gif) animImg.src = gif; }
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

/** 有识别结果就展示，不再做置信度门槛判断 */
function renderRecognized(rec, opts = {}) {
  if (!rec) return;
  const tileName    = TILE_LABEL[rec.label] || rec.label;
  const displayText = tileName + " ✅ 识别成功";
  const conf        = "置信度 " + Math.round(rec.confidence * 100) + "%";

  // Nav mode
  const recTile = $("rec-tile");
  const recConf = $("rec-conf");
  if (recTile) recTile.textContent = displayText;
  if (recConf) recConf.textContent = conf;

  // Play mode
  const rv = $("tile-result-value");
  const rc = $("tile-result-conf");
  if (rv) rv.textContent = displayText;
  if (rc) rc.textContent = conf;
}

/** 无识别结果时清空展示，避免一直显示上一次的「识别成功」 */
function clearRecognized() {
  const recTile = $("rec-tile");
  const recConf = $("rec-conf");
  const rv = $("tile-result-value");
  const rc = $("tile-result-conf");
  if (recTile) recTile.textContent = "—";
  if (recConf) recConf.textContent = "";
  if (rv) rv.textContent = "—";
  if (rc) rc.textContent = "";
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
    appendLog("[CAM] 摄像头已连接，点「开始自动识别」启动流程");
    setAvatar("idle", "摄像头就绪，点「开始自动识别」");

    const camBtn = $("cam-btn");
    if (camBtn) camBtn.textContent = "✅ 摄像头已开";
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
    if (r.ok && r.recognized) {
      renderRecognized(r.recognized);
      const lbl = TILE_LABEL[r.recognized.label] || r.recognized.label;
      setAvatar("done", `识别到：${lbl}`);
      appendLog(`[CAM] 识别: ${r.recognized.label} (${Math.round(r.recognized.confidence * 100)}%)`);
    } else {
      clearRecognized();
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

// ===== Auto-recognition loop =====
// 3-step split flow (browser provides camera frame to avoid device conflict):
//   Step 1: POST /arm/start_scene  → server: TTS + pick + present (blocks ~2s)
//   Step 2: browser captures frame from webcam
//   Step 3: POST /capture_frame    → HistogramVision identifies → show result immediately
//   Step 4: POST /execute_scene    → arm throws/returns + closing TTS

let autoRunning = false; // prevents getStatus() from overriding avatar mid-flow

async function captureFrame() {
  const video  = $("camera-feed");
  const canvas = $("camera-canvas");
  if (!cameraStream || !video || video.readyState < 2) return null;
  // 缩图到 480×360（~25KB vs ~250KB），KIMI Vision 推理快 ~3x，质量识别牌面够用
  canvas.width  = 480;
  canvas.height = 360;
  canvas.getContext("2d").drawImage(video, 0, 0, 480, 360);
  return canvas.toDataURL("image/jpeg", 0.75).split(",")[1];
}

async function autoLoopTick() {
  if (!autoLoopActive || autoLoopCooldown || prevBusy) return;
  autoLoopCooldown = true;
  autoRunning = true;

  const style = $("style")?.value || "polite";
  const safe  = ($("safe")?.value !== "false");

  // Reset recognition display
  const rv = $("tile-result-value");
  const rc = $("tile-result-conf");
  const recTile = $("rec-tile");
  const recConf = $("rec-conf");
  if (rv) rv.textContent = "识别中...";
  if (rc) rc.textContent = "";
  if (recTile) recTile.textContent = "识别中...";
  if (recConf) recConf.textContent = "";

  try {
    // ── Step 1: TTS + arm pick + present (server blocks ~2s) ──────────────
    setAvatar("acting", "来！开牌...");
    appendLog("[AUTO] Step1: 开牌 → 机械臂抓牌展示");
    const step1 = await fetch(`/arm/start_scene?style=${style}&safe=${safe}`, { method: "POST" })
      .then(r => r.json()).catch(() => ({ ok: false, error: "network" }));
    if (!step1.ok) {
      appendLog("[AUTO] Step1 失败: " + (step1.error || "unknown"));
      setAvatar("error", "机械臂准备失败");
      autoRunning = false;
      setTimeout(() => { autoLoopCooldown = false; }, AUTO_COOLDOWN_MS);
      return;
    }

    // ── Step 2+3: Burst capture after arm stabilizes (≤1s) ───────────────
    setAvatar("thinking", "扫描牌面...");
    appendLog("[AUTO] Step2: 臂已就位，连续采帧...");

    if (!cameraStream) await startCamera();
    if (!cameraStream) {
      appendLog("[AUTO] Step2: 摄像头未就绪");
      setAvatar("error", "摄像头未就绪");
      autoRunning = false;
      setTimeout(() => { autoLoopCooldown = false; }, AUTO_COOLDOWN_MS);
      return;
    }

    // Burst: up to 4 frames, 200ms apart — take highest confidence, stop early at ≥85%
    const BURST_FRAMES = 4;
    const BURST_GAP_MS = 200;
    let bestResult = null;

    for (let i = 0; i < BURST_FRAMES; i++) {
      if (i > 0) await new Promise(r => setTimeout(r, BURST_GAP_MS));
      const b64 = await captureFrame();
      if (!b64) continue;
      const r = await post("/capture_frame", { image: b64 });
      if (!r.ok || !r.recognized) continue;
      const conf = r.recognized.confidence;
      appendLog(`[AUTO] Step3 f${i+1}: ${r.recognized.label} conf=${Math.round(conf*100)}%`);
      if (!bestResult || conf > bestResult.recognized.confidence) {
        bestResult = r;
        renderRecognized(r.recognized);
      }
      if (conf >= 0.85) break; // good enough, stop early
    }

    if (!bestResult || !bestResult.recognized) {
      appendLog("[AUTO] Step3: 所有帧识别失败");
      clearRecognized();
      const rv = $("tile-result-value");
      const recTile = $("rec-tile");
      if (rv) rv.textContent = "识别失败";
      if (recTile) recTile.textContent = "识别失败";
      setAvatar("error", "识别失败");
      autoRunning = false;
      setTimeout(() => { autoLoopCooldown = false; }, AUTO_COOLDOWN_MS);
      return;
    }
    const { label, confidence } = bestResult.recognized;
    const confPct = Math.round(confidence * 100);
    appendLog(`[AUTO] Step3: 最终 → ${label} conf=${confPct}%`);

    // ── Step 4: Determine scene + execute arm action ──────────────────────
    const scene = label === "white_dragon" ? "A" : "B";
    appendLog(`[AUTO] Step4: Scene ${scene} — ${scene === "A" ? "扔出 → 我要验牌" : "退回 → 牌没有问题"}`);
    setAvatar("acting", scene === "A" ? "扔出！" : "退回！");
    playSceneVideo(scene);

    const t0   = Date.now();
    const exec = await post("/execute_scene", {
      scene, style, safe,
      recognized_label: label,
      recognized_conf:  confidence,
    });
    const ms = Date.now() - t0;

    if (exec.ok) {
      history.push({ scene, ok: true, ms, label, conf: confidence, style });
      renderStats();
      renderHistory();
      setAvatar("done", scene === "A" ? "扔出！我要验牌！" : "退回！牌没有问题！");
      appendLog(`[AUTO] 完成 Scene ${scene} dt=${(ms/1000).toFixed(1)}s`);
    } else {
      appendLog(`[AUTO] Step4 失败: ${exec.error_code || "unknown"}`);
      setAvatar("error", "执行失败");
    }

  } catch (e) {
    appendLog("[AUTO] 异常: " + e.message);
    setAvatar("error", "网络异常");
  }

  autoRunning = false;
  setTimeout(() => {
    autoLoopCooldown = false;
    if (autoLoopActive) setAvatar("idle", "等待下次触发...");
  }, 3000);
}

function toggleAutoLoop() {
  autoLoopActive = !autoLoopActive;
  const btn = $("auto-loop-btn");

  if (autoLoopActive) {
    autoLoopCooldown = false;
    if (btn) { btn.textContent = "⏹ 停止"; btn.classList.add("active"); }

    // 3s 倒计时后自动触发第一次开牌
    if (countdownTimer) clearTimeout(countdownTimer);
    let secs = 3;
    setAvatar("thinking", `${secs}秒后开牌...`);
    appendLog(`[AUTO] 自动识别启动 — ${secs}秒后触发开牌`);
    const tick = () => {
      secs--;
      if (secs > 0) {
        setAvatar("thinking", `${secs}秒后开牌...`);
        countdownTimer = setTimeout(tick, 1000);
      } else {
        countdownTimer = null;
        appendLog("[AUTO] 倒计时结束 → 触发开牌");
        autoLoopTick();
      }
    };
    countdownTimer = setTimeout(tick, 1000);

    // 不使用 setInterval 持续循环 — 改由 OpenClaw /trigger 驱动单次执行
  } else {
    if (countdownTimer) { clearTimeout(countdownTimer); countdownTimer = null; }
    if (autoLoopTimer)  { clearInterval(autoLoopTimer); autoLoopTimer = null; }
    autoLoopCooldown = false;
    if (btn) { btn.textContent = "🎯 开始自动识别"; btn.classList.remove("active"); }
    setAvatar("idle");
    appendLog("[AUTO] 自动识别已停止");
  }
}

// Called by "开牌！" button — fire one full scene cycle immediately
function triggerOnce() {
  if (!autoLoopActive) {
    appendLog("[WATCH] 请先点「开始自动识别」进入监听模式");
    return;
  }
  if (autoLoopCooldown || autoRunning || prevBusy) {
    appendLog("[WATCH] 正在执行中，请稍候...");
    return;
  }
  appendLog("[WATCH] 手动触发开牌 → 执行识别流程");
  autoLoopTick();
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

    // Skip avatar updates while autoLoopTick is managing state manually
    if (!autoRunning) {
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
      if (j.recognized) renderRecognized(j.recognized);
      else clearRecognized();
    }
    prevBusy = j.busy;

    // Activate Mode: OpenClaw calls POST /activate → auto-start camera + AutoLoop
    if (j.activate_pending) {
      appendLog("[WATCH] 收到远程激活信号 → 自动开摄像头 + 启动 AutoLoop");
      if (!cameraStream) await startCamera();
      if (!autoLoopActive) toggleAutoLoop();
    }

    // Watch Mode: server sets trigger_pending (via POST /trigger or OpenClaw)
    // → auto-fire one scene cycle
    if (j.trigger_pending && autoLoopActive && !autoLoopCooldown && !autoRunning) {
      appendLog("[WATCH] 收到外部开牌触发 → 执行识别流程");
      autoLoopTick();
    }

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
  playSceneVideo(scene);

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

async function runAutoScene() {
  const style = $("style").value;
  const safe  = $("safe").value === "true";

  setAvatar("acting", "自动对局中...");
  $("qbtn-auto").classList.add("active");

  const t0 = Date.now();
  const r  = await post("/auto_run", { style, safe });
  const ms = Date.now() - t0;

  $("qbtn-auto").classList.remove("active");

  const scene = r.scene || "A";
  const recognized = (r.label) ? { label: r.label, confidence: r.confidence } : null;
  if (recognized) renderRecognized(recognized);

  history.push({
    scene, ok: r.ok, ms,
    label: r.label || null,
    conf:  r.confidence || 0,
    style,
  });
  renderStats();
  renderHistory();

  setAvatar(r.ok ? "done" : "error",
    r.ok
      ? `识别: ${r.label || '?'} → Scene ${scene}`
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

// ===== Calibration =====
async function calibFromCamera(label) {
  const labelName = label === "white_dragon" ? "白板" : "一饼";
  const hint = $("calib-hint");

  // Must use browser webcam so calibration & recognition share the same image source
  if (!cameraStream) {
    appendLog("[CALIB] 请先点「开启摄像头」");
    if (hint) hint.textContent = "请先开启摄像头";
    return;
  }
  const base64 = await captureFrame();
  if (!base64) {
    appendLog("[CALIB] 截帧失败");
    if (hint) hint.textContent = "截帧失败，请重试";
    return;
  }

  if (hint) hint.textContent = `正在标定 ${labelName}...`;
  appendLog(`[CALIB] 标定 ${labelName} (${label})`);

  try {
    const res = await fetch(`/calibrate?label=${label}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: base64 }),
    });
    const r = await res.json();
    if (r.ok) {
      appendLog(`[CALIB] ${labelName} 标定成功 ✅`);
      if (hint) hint.textContent = `${labelName} 标定成功！`;
    } else {
      appendLog(`[CALIB] ${labelName} 标定失败: ${r.error || "未知"}`);
      if (hint) hint.textContent = `标定失败: ${r.error || "未知"}`;
    }
    if (r.calibration) updateCalibStatus(r.calibration);
  } catch (e) {
    appendLog("[CALIB] 请求失败: " + e.message);
    if (hint) hint.textContent = "请求失败: " + e.message;
  }
}

async function fetchCalibStatus() {
  try {
    const res = await fetch("/calibrate");
    const r   = await res.json();
    if (r.calibration) updateCalibStatus(r.calibration);
  } catch (_) {}
}

function updateCalibStatus(cal) {
  const chipWhite = $("calib-white");
  const chipOne   = $("calib-one");
  const hasWhite  = !!cal.white_dragon;
  const hasOne    = !!cal.one_dot;

  if (chipWhite) {
    chipWhite.textContent = hasWhite ? "白板 ✅" : "白板 ⬜";
    chipWhite.className   = "calib-chip" + (hasWhite ? " ok" : "");
  }
  if (chipOne) {
    chipOne.textContent = hasOne ? "一饼 ✅" : "一饼 ⬜";
    chipOne.className   = "calib-chip" + (hasOne ? " ok" : "");
  }

  const hint = $("calib-hint");
  if (hint && hasWhite && hasOne) {
    hint.textContent = "两张牌已标定 — 可以开始自动识别 🎯";
  } else if (hint && !hasWhite && !hasOne) {
    hint.textContent = "将牌放到摄像头前，点击按钮标定";
  } else if (hint) {
    hint.textContent = "还需标定：" + (!hasWhite ? "白板 " : "") + (!hasOne ? "一饼" : "");
  }
}

// ===== Init =====
syncSelectors();
setAvatar("idle");
setInterval(getStatus, 800);
getStatus();
// Poll calibration status on load
fetchCalibStatus();

// Sync both scene videos to Scene A's natural aspect ratio
(function syncVideoAspectRatio() {
  const vA = $("avatar-video-scene-a");
  const vB = $("avatar-video-scene-b");
  if (!vA || !vB) return;
  vA.addEventListener("loadedmetadata", () => {
    const ar = vA.videoWidth + " / " + vA.videoHeight;
    vA.style.aspectRatio = ar;
    vB.style.aspectRatio = ar;
  }, { once: true });
})();
