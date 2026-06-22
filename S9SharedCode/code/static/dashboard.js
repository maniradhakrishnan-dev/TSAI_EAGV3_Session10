/* ═══════════════════════════════════════════════════════════════════
   Computer-Use Agent Dashboard — Client-side Logic
   ═══════════════════════════════════════════════════════════════════ */

let ws = null;
let isRunning = false;
let runStartTime = null;

// ─── WebSocket ─────────────────────────────────────────────────

function connectWebSocket() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(`${proto}//${location.host}/ws`);

  ws.onopen = () => {
    document.getElementById('ws-status').className = 'status-dot connected';
    document.getElementById('ws-status-text').textContent = 'Connected';
  };

  ws.onclose = () => {
    document.getElementById('ws-status').className = 'status-dot error';
    document.getElementById('ws-status-text').textContent = 'Disconnected';
    setTimeout(connectWebSocket, 3000);
  };

  ws.onerror = () => {
    document.getElementById('ws-status').className = 'status-dot error';
  };

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    handleMessage(msg);
  };
}

function handleMessage(msg) {
  switch (msg.type) {
    case 'init':
      if (msg.history) renderHistory(msg.history);
      if (msg.current_run) {
        isRunning = true;
        updateRunButton();
        showResultRunning(msg.current_run);
      }
      break;
    case 'log':
      appendLog(msg.text);
      break;
    case 'status':
      if (msg.status === 'running') {
        runStartTime = Date.now();
        isRunning = true;
        updateRunButton();
        clearLog();
        showResultRunning(msg);
        appendLog(`▶ Starting: ${msg.app} — "${msg.goal}"`);
      }
      break;
    case 'result':
      isRunning = false;
      updateRunButton();
      showResult(msg);
      renderHistory(null, msg);
      break;
    case 'error':
      appendLog(`⚠ ${msg.text}`, 'error');
      break;
  }
}

// ─── Log viewer ────────────────────────────────────────────────

function clearLog() {
  document.getElementById('log-output').innerHTML = '';
}

function appendLog(text, cls) {
  const el = document.getElementById('log-output');
  const placeholder = el.querySelector('.log-placeholder');
  if (placeholder) placeholder.remove();

  // Auto-detect log class
  if (!cls) {
    if (text.includes('SUCCESS') || text.includes('✅')) cls = 'success';
    else if (text.includes('FAIL') || text.includes('❌') || text.includes('Error')) cls = 'error';
    else if (text.includes('Layer')) cls = 'layer';
    else cls = 'info';
  }

  const span = document.createElement('span');
  span.className = `log-line ${cls}`;
  span.textContent = text + '\n';
  el.appendChild(span);
  el.scrollTop = el.scrollHeight;
}

// ─── Result panel ──────────────────────────────────────────────

function showResultRunning(data) {
  document.getElementById('result-placeholder').classList.add('hidden');
  const content = document.getElementById('result-content');
  content.classList.remove('hidden');

  const badge = document.getElementById('result-status-badge');
  badge.textContent = '● Running…';
  badge.className = 'result-status running';

  document.getElementById('r-app').textContent = data.app || '—';
  document.getElementById('r-path').textContent = '…';
  document.getElementById('r-turns').textContent = '…';
  document.getElementById('r-duration').textContent = '…';
  document.getElementById('r-content').textContent = '…';
  document.getElementById('r-error-row').classList.add('hidden');
}

function showResult(data) {
  document.getElementById('result-placeholder').classList.add('hidden');
  const content = document.getElementById('result-content');
  content.classList.remove('hidden');

  const r = data.result || {};
  const success = r.success;
  const badge = document.getElementById('result-status-badge');
  badge.textContent = success ? '✓ Success' : '✗ Failed';
  badge.className = `result-status ${success ? 'success' : 'failed'}`;

  document.getElementById('r-app').textContent = r.app || data.app || '—';
  document.getElementById('r-path').textContent = r.path || '—';
  document.getElementById('r-turns').textContent = r.turns ?? '—';
  document.getElementById('r-content').textContent = r.content || '—';

  const duration = runStartTime ? ((Date.now() - runStartTime) / 1000).toFixed(1) + 's' : '—';
  document.getElementById('r-duration').textContent = duration;

  if (r.error) {
    document.getElementById('r-error-row').classList.remove('hidden');
    document.getElementById('r-error').textContent = r.error;
  } else {
    document.getElementById('r-error-row').classList.add('hidden');
  }
}

// ─── Run button ────────────────────────────────────────────────

function updateRunButton() {
  const btn = document.getElementById('btn-run');
  const stopBtn = document.getElementById('btn-stop');
  if (isRunning) {
    btn.disabled = true;
    btn.classList.add('running');
    btn.innerHTML = '<span class="btn-icon">◌</span> Running…';
    if (stopBtn) stopBtn.style.display = 'inline-block';
  } else {
    btn.disabled = false;
    btn.classList.remove('running');
    btn.innerHTML = '<span class="btn-icon">▶</span> Run Task';
    if (stopBtn) stopBtn.style.display = 'none';
  }
}

function stopTask() {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  ws.send(JSON.stringify({ action: 'stop_task' }));
}

function runTask() {
  if (isRunning || !ws || ws.readyState !== WebSocket.OPEN) return;

  const app = document.getElementById('app-select').value;
  const goal = document.getElementById('goal-input').value.trim();
  const layer = document.getElementById('layer-select').value || null;

  if (!goal) {
    appendLog('⚠ Please enter a goal.', 'error');
    return;
  }

  ws.send(JSON.stringify({
    action: 'run_task',
    task: { app, goal, force_path: layer }
  }));
}

// ─── Presets ───────────────────────────────────────────────────

async function loadPresets() {
  try {
    const res = await fetch('/api/presets');
    const data = await res.json();
    const grid = document.getElementById('preset-grid');
    grid.innerHTML = '';

    for (const p of data.presets) {
      const card = document.createElement('div');
      card.className = 'preset-card';
      card.onclick = () => applyPreset(p);
      card.innerHTML = `
        <div class="preset-icon">${p.icon}</div>
        <div class="preset-name">${p.name}</div>
        <div class="preset-desc">${p.description}</div>
        <div class="preset-tags">${p.tags.map(t => `<span class="tag">${t}</span>`).join('')}</div>
      `;
      grid.appendChild(card);
    }
  } catch (e) {
    console.error('Failed to load presets:', e);
  }
}

function applyPreset(p) {
  document.getElementById('app-select').value = p.app;
  document.getElementById('goal-input').value = p.goal;
  document.getElementById('layer-select').value = p.force_path || '';
  // Smooth scroll to form
  document.querySelector('.form-card').scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// ─── History ──────────────────────────────────────────────────

function renderHistory(history, newRun) {
  const body = document.getElementById('history-body');
  const empty = document.getElementById('history-empty');

  if (newRun) {
    const r = newRun.result || {};
    const row = document.createElement('tr');
    const ts = newRun.completed_at || newRun.started_at || new Date().toISOString();
    const time = new Date(ts).toLocaleTimeString();
    const status = r.success ? 'success' : (newRun.status === 'running' ? 'running' : 'failed');
    row.innerHTML = `
      <td>${time}</td>
      <td>${newRun.app || '—'}</td>
      <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${newRun.goal || '—'}</td>
      <td>${r.path || '—'}</td>
      <td><span class="badge ${status}">${status}</span></td>
    `;
    body.insertBefore(row, body.firstChild);
    empty.classList.add('hidden');
    return;
  }

  if (!history || history.length === 0) {
    empty.classList.remove('hidden');
    return;
  }

  empty.classList.add('hidden');
  body.innerHTML = '';
  for (const run of [...history].reverse()) {
    const r = run.result || {};
    const row = document.createElement('tr');
    const ts = run.completed_at || run.started_at || '';
    const time = ts ? new Date(ts).toLocaleTimeString() : '—';
    const status = r.success ? 'success' : (run.status === 'running' ? 'running' : 'failed');
    row.innerHTML = `
      <td>${time}</td>
      <td>${run.app || '—'}</td>
      <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${run.goal || '—'}</td>
      <td>${r.path || '—'}</td>
      <td><span class="badge ${status}">${status}</span></td>
    `;
    body.appendChild(row);
  }
}

// ─── Navigation ───────────────────────────────────────────────

document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', () => {
    const view = link.dataset.view;
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    link.classList.add('active');
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById(`view-${view}`).classList.add('active');
    document.getElementById('page-title').textContent =
      view.charAt(0).toUpperCase() + view.slice(1);
  });
});

// Allow Enter in goal textarea to NOT submit (Shift+Enter for newline is natural)
document.getElementById('goal-input').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    runTask();
  }
});

// ─── Init ─────────────────────────────────────────────────────

connectWebSocket();
loadPresets();
