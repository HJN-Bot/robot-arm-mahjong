// ===== State =====
const history = [];   // { scene, ok, label, conf, ms, style }
let prevBusy = false;

// Avatar state -> display mapping
const AVATAR_STATE = {
  idle:     { badge: "待机",   emoji: "🤖", speech: "等待指令...", cls: "" },
  thinking: { badge: "思考中", emoji: "🤔", speech: "让我看看...",  cls: "thinking" },
  acting:   { badge: "执行中", emoji: "🦾", speech: "动起来！",    cls: "acting" },
  done:     { badge: "完成",   emoji: "😎", speech: "",            cls: "done" },
  error:    { badge: "出错",   emoji: "😵", speech: "出了点问题...", cls: "error" },
};

const TILE_LABEL = {
  white_dragon: "白板 🀙",
  one_dot:      "一筒 🀇",
};

// ===== DOM helpers =====
const $ = id => document.getElementById(id);

function setAvatar(stateKey, speechOverride) {
  const s = AVATAR_STATE[stateKey] || AVATAR_STATE.idle;
  const frame = $("avatar-frame");
  frame.className = "avatar-frame " + s.cls;
  $("avatar-emoji").textContent = s.emoji;
  $("avatar-state").textContent = s.badge;
  $("speech-text").textContent = speechOverride || s.speech;
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
  $("rec-tile").textContent = TILE_LABEL[rec.label] || rec.label;
  $("rec-conf").textContent = "置信度 " + Math.round(rec.confidence * 100) + "%";
}

function renderStats() {
  $("stat-total").textContent = history.length;
  if (history.length === 0) return;
  const ok = history.filter(r => r.ok).length;
  $("stat-success").textContent = Math.round(ok / history.length * 100) + "%";
  const avg = history.reduce((s, r) => s + r.ms, 0) / history.length;
  $("stat-avg").textContent = (avg / 1000).toFixed(1) + "s";
}

function renderHistory() {
  const tbody = $("history-body");
  if (history.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="empty-row">暂无记录</td></tr>';
    return;
  }
  tbody.innerHTML = [...history].reverse().slice(0, 30).map((r, i) => {
    const n = history.length - i;
    const ok  = r.ok ? '<span class="badge-ok">✓ 成功</span>' : '<span class="badge-fail">✗ 失败</span>';
    const sc  = `<span class="badge-${r.scene.toLowerCase()}">${r.scene}</span>`;
    const tile = r.label ? (TILE_LABEL[r.label] || r.label) : "—";
    return `<tr><td>${n}</td><td>${sc}</td><td>${ok}</td><td>${tile}</td><td>${(r.ms/1000).toFixed(2)}s</td><td>${r.style}</td></tr>`;
  }).join("");
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
    } else if (!j.busy) {
      // keep current state unless idle
    }
    prevBusy = j.busy;

    if (j.recognized) renderRecognized(j.recognized);
    $("logs").textContent = (j.logs || []).slice(-80).join("\n");
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

  // optimistic UI
  setAvatar("acting", scene === "A" ? "抓牌，扔出！" : "抓牌，退回！");
  const card = $(scene === "A" ? "skill-a" : "skill-b");
  card.classList.add("active");

  const t0 = Date.now();
  const r = await post("/run_scene", { scene, style, safe });
  const ms = Date.now() - t0;

  card.classList.remove("active");

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
    r.ok ? (scene === "A" ? "我要验牌！" : "牌退回去了。") : "哎，失败了...");
  setTimeout(() => setAvatar("idle"), 3000);
  await getStatus();
}

async function runExtra(action) {
  setAvatar("acting", { tap: "点三点！", nod: "点头 ✅", shake: "摇头 ❌" }[action]);
  await post(`/${action}`, {});
  setTimeout(() => setAvatar("idle"), 2000);
}

// ===== Init =====
setInterval(getStatus, 800);
getStatus();
