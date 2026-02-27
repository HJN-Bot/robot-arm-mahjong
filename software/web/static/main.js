async function getStatus() {
  const res = await fetch('/status');
  const j = await res.json();
  document.getElementById('status').textContent = JSON.stringify(j, null, 2);
  document.getElementById('logs').textContent = (j.logs || []).slice(-80).join('\n');
}

async function post(path, body) {
  await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : '{}',
  });
  await getStatus();
}

async function runScene(scene) {
  const style = document.getElementById('style').value;
  const safe = document.getElementById('safe').value === 'true';
  await post('/run_scene', { scene, style, safe });
}

setInterval(getStatus, 800);
getStatus();
