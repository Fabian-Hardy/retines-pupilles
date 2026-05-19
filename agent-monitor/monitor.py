#!/usr/bin/env python3
"""
Rétines & Pupilles — Agent Monitor
Serveur local qui reçoit les événements des hooks Claude Code
et sert un dashboard temps réel dans le navigateur.

Usage:
    python monitor.py

Puis ouvrir http://localhost:7777 dans le navigateur.
"""

import json
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from collections import deque

# ─── État global ──────────────────────────────────────────────
events = deque(maxlen=200)
sessions = {}
current_session = {"id": None, "model": None, "agent": None, "status": "idle", "start": None}
sse_clients = []
lock = threading.Lock()

# ─── HTML Dashboard ───────────────────────────────────────────
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Agent Monitor — Rétines & Pupilles</title>
<style>
  :root {
    --bg: #0f1117;
    --surface: #1a1d27;
    --border: #2a2d3e;
    --text: #e2e8f0;
    --muted: #64748b;
    --accent: #6366f1;
    --green: #22c55e;
    --yellow: #eab308;
    --red: #ef4444;
    --blue: #3b82f6;
    --orange: #f97316;
    --purple: #a855f7;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: var(--bg); color: var(--text); font-family: 'SF Mono', 'Fira Code', monospace; font-size: 13px; }

  header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 14px 24px; background: var(--surface); border-bottom: 1px solid var(--border);
    position: sticky; top: 0; z-index: 100;
  }
  .logo { display: flex; align-items: center; gap: 10px; }
  .logo-icon { width: 32px; height: 32px; background: var(--accent); border-radius: 8px;
    display: flex; align-items: center; justify-content: center; font-size: 16px; }
  .logo h1 { font-size: 15px; font-weight: 600; color: var(--text); letter-spacing: 0.3px; }
  .logo span { font-size: 11px; color: var(--muted); }

  .status-badge {
    display: flex; align-items: center; gap: 8px;
    padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 500;
    background: var(--border); border: 1px solid var(--border);
    transition: all 0.3s;
  }
  .status-badge.active { background: rgba(34,197,94,0.1); border-color: var(--green); color: var(--green); }
  .status-badge.idle { background: rgba(100,116,139,0.1); border-color: var(--muted); color: var(--muted); }
  .pulse { width: 8px; height: 8px; border-radius: 50%; background: currentColor; }
  .pulse.anim { animation: pulse 1.5s infinite; }
  @keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.5;transform:scale(0.8)} }

  main { display: grid; grid-template-columns: 320px 1fr; gap: 0; height: calc(100vh - 57px); overflow: hidden; }

  .sidebar {
    background: var(--surface); border-right: 1px solid var(--border);
    display: flex; flex-direction: column; overflow: hidden;
  }
  .sidebar-section { padding: 16px; border-bottom: 1px solid var(--border); }
  .sidebar-section h3 { font-size: 10px; text-transform: uppercase; letter-spacing: 1.2px; color: var(--muted); margin-bottom: 12px; }

  .stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .stat {
    background: var(--bg); border: 1px solid var(--border); border-radius: 8px;
    padding: 10px 12px;
  }
  .stat .label { font-size: 10px; color: var(--muted); margin-bottom: 4px; }
  .stat .value { font-size: 18px; font-weight: 700; color: var(--text); }
  .stat .value.model { font-size: 11px; word-break: break-all; }

  .model-chip {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 500;
    background: rgba(99,102,241,0.15); border: 1px solid rgba(99,102,241,0.4); color: #818cf8;
  }
  .model-chip.sonnet { background: rgba(99,102,241,0.15); border-color: rgba(99,102,241,0.4); color: #818cf8; }
  .model-chip.opus { background: rgba(168,85,247,0.15); border-color: rgba(168,85,247,0.4); color: #c084fc; }
  .model-chip.haiku { background: rgba(34,197,94,0.15); border-color: rgba(34,197,94,0.4); color: #4ade80; }

  .agent-list { display: flex; flex-direction: column; gap: 6px; }
  .agent-item {
    display: flex; align-items: center; gap: 10px;
    padding: 8px 10px; border-radius: 6px; background: var(--bg);
    border: 1px solid var(--border);
  }
  .agent-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
  .agent-dot.working { background: var(--green); box-shadow: 0 0 6px var(--green); animation: pulse 1.5s infinite; }
  .agent-dot.done { background: var(--muted); }
  .agent-name { flex: 1; font-size: 11px; color: var(--text); }
  .agent-tool { font-size: 10px; color: var(--muted); }

  .feed { flex: 1; overflow-y: auto; padding: 0; }
  .feed::-webkit-scrollbar { width: 4px; }
  .feed::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

  .content { padding: 16px 20px; overflow-y: auto; height: 100%; }
  .content::-webkit-scrollbar { width: 4px; }
  .content::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

  .event {
    display: flex; gap: 12px; padding: 8px 16px;
    border-bottom: 1px solid rgba(42,45,62,0.5);
    transition: background 0.2s;
  }
  .event:hover { background: rgba(255,255,255,0.02); }
  .event-time { color: var(--muted); font-size: 10px; min-width: 60px; padding-top: 2px; }
  .event-body { flex: 1; }
  .event-title { font-size: 12px; margin-bottom: 2px; }
  .event-detail { font-size: 10px; color: var(--muted); }
  .event-icon { font-size: 14px; min-width: 20px; text-align: center; }

  .tag {
    display: inline-block; padding: 1px 6px; border-radius: 4px; font-size: 10px;
    margin-left: 6px; vertical-align: middle;
  }
  .tag.bash { background: rgba(234,179,8,0.15); color: #fbbf24; }
  .tag.read { background: rgba(59,130,246,0.15); color: #60a5fa; }
  .tag.write { background: rgba(249,115,22,0.15); color: #fb923c; }
  .tag.edit { background: rgba(249,115,22,0.15); color: #fb923c; }
  .tag.web { background: rgba(34,197,94,0.15); color: #4ade80; }
  .tag.agent { background: rgba(168,85,247,0.15); color: #c084fc; }
  .tag.grep { background: rgba(99,102,241,0.15); color: #818cf8; }
  .tag.glob { background: rgba(99,102,241,0.15); color: #818cf8; }

  .empty-state {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    height: 100%; gap: 12px; color: var(--muted);
  }
  .empty-state .icon { font-size: 48px; opacity: 0.3; }
  .empty-state p { font-size: 12px; }

  #conn-status {
    position: fixed; bottom: 16px; right: 16px;
    font-size: 11px; padding: 6px 12px; border-radius: 6px;
    background: var(--surface); border: 1px solid var(--border);
    color: var(--muted);
  }
</style>
</head>
<body>

<header>
  <div class="logo">
    <div class="logo-icon">👁</div>
    <div>
      <h1>Agent Monitor</h1>
      <span>Rétines & Pupilles</span>
    </div>
  </div>
  <div class="status-badge idle" id="global-status">
    <div class="pulse" id="pulse-dot"></div>
    <span id="status-text">Inactif</span>
  </div>
</header>

<main>
  <div class="sidebar">
    <div class="sidebar-section">
      <h3>Session courante</h3>
      <div class="stat-grid">
        <div class="stat">
          <div class="label">Modèle</div>
          <div class="value model" id="current-model">—</div>
        </div>
        <div class="stat">
          <div class="label">Durée</div>
          <div class="value" id="session-duration">—</div>
        </div>
        <div class="stat">
          <div class="label">Outils appelés</div>
          <div class="value" id="tool-count">0</div>
        </div>
        <div class="stat">
          <div class="label">Agents actifs</div>
          <div class="value" id="agent-count">0</div>
        </div>
      </div>
    </div>

    <div class="sidebar-section">
      <h3>Agents</h3>
      <div class="agent-list" id="agent-list">
        <div style="color: var(--muted); font-size: 11px;">Aucun agent actif</div>
      </div>
    </div>

    <div class="sidebar-section" style="flex:1; overflow:hidden; display:flex; flex-direction:column;">
      <h3>Flux d'événements</h3>
      <div class="feed" id="event-feed">
        <div style="padding:20px; color: var(--muted); font-size: 11px; text-align:center;">
          En attente d'événements...
        </div>
      </div>
    </div>
  </div>

  <div class="content" id="main-content">
    <div class="empty-state">
      <div class="icon">🤖</div>
      <p>Lance Claude Code pour voir l'activité en temps réel</p>
      <p style="font-size:10px; margin-top:4px;">Écoute sur localhost:7777</p>
    </div>
  </div>
</main>

<div id="conn-status">⚡ Connexion SSE active</div>

<script>
const state = { tools: 0, agents: {}, sessionStart: null, model: null };

function getTagClass(tool) {
  const t = (tool||'').toLowerCase();
  if (t.includes('bash')) return 'bash';
  if (t.includes('read')) return 'read';
  if (t.includes('write')) return 'write';
  if (t.includes('edit')) return 'edit';
  if (t.includes('web') || t.includes('fetch') || t.includes('search')) return 'web';
  if (t.includes('agent') || t.includes('task')) return 'agent';
  if (t.includes('grep')) return 'grep';
  if (t.includes('glob')) return 'glob';
  return 'bash';
}

function getModelClass(model) {
  if (!model) return '';
  if (model.includes('opus')) return 'opus';
  if (model.includes('haiku')) return 'haiku';
  return 'sonnet';
}

function getModelShort(model) {
  if (!model) return '—';
  if (model.includes('opus')) return 'Opus 4';
  if (model.includes('haiku')) return 'Haiku 4.5';
  if (model.includes('sonnet')) return 'Sonnet 4.5';
  return model;
}

function formatDuration(ms) {
  if (ms < 1000) return ms + 'ms';
  if (ms < 60000) return (ms/1000).toFixed(1) + 's';
  return Math.floor(ms/60000) + 'm ' + Math.floor((ms%60000)/1000) + 's';
}

function addEventToFeed(ev) {
  const feed = document.getElementById('event-feed');
  const first = feed.querySelector('div[style]');
  if (first && first.textContent.includes('En attente')) first.remove();

  const icons = { pre_tool: '⚙️', post_tool: '✅', stop: '🏁', start: '🚀', agent_start: '🤖', agent_done: '✔️' };
  const icon = icons[ev.type] || '•';
  const time = new Date(ev.timestamp * 1000).toLocaleTimeString('fr-BE', {hour:'2-digit',minute:'2-digit',second:'2-digit'});
  const tagClass = getTagClass(ev.tool);

  let title = ev.tool || ev.type;
  let detail = ev.detail || '';

  const el = document.createElement('div');
  el.className = 'event';
  el.innerHTML = `
    <div class="event-time">${time}</div>
    <div class="event-icon">${icon}</div>
    <div class="event-body">
      <div class="event-title">
        ${title}
        ${ev.tool ? `<span class="tag ${tagClass}">${ev.tool}</span>` : ''}
        ${ev.model ? `<span class="tag ${getModelClass(ev.model)}">${getModelShort(ev.model)}</span>` : ''}
      </div>
      ${detail ? `<div class="event-detail">${detail}</div>` : ''}
    </div>
  `;
  feed.insertBefore(el, feed.firstChild);
}

function updateAgentList() {
  const list = document.getElementById('agent-list');
  const agents = Object.values(state.agents);
  if (agents.length === 0) {
    list.innerHTML = '<div style="color: var(--muted); font-size: 11px;">Aucun agent actif</div>';
    return;
  }
  list.innerHTML = agents.map(a => `
    <div class="agent-item">
      <div class="agent-dot ${a.status === 'working' ? 'working' : 'done'}"></div>
      <div class="agent-name">${a.name || 'Agent principal'}</div>
      <div class="agent-tool">${a.currentTool || ''}</div>
    </div>
  `).join('');
  document.getElementById('agent-count').textContent = agents.filter(a => a.status === 'working').length;
}

function processEvent(ev) {
  addEventToFeed(ev);

  if (ev.type === 'start' || ev.type === 'pre_tool') {
    if (ev.model) {
      state.model = ev.model;
      document.getElementById('current-model').innerHTML =
        `<span class="model-chip ${getModelClass(ev.model)}">${getModelShort(ev.model)}</span>`;
    }
    if (!state.sessionStart) {
      state.sessionStart = Date.now();
      setInterval(() => {
        if (state.sessionStart)
          document.getElementById('session-duration').textContent =
            formatDuration(Date.now() - state.sessionStart);
      }, 1000);
    }
    const badge = document.getElementById('global-status');
    badge.className = 'status-badge active';
    document.getElementById('status-text').textContent = 'Actif';
    document.getElementById('pulse-dot').classList.add('anim');
  }

  if (ev.type === 'pre_tool') {
    state.tools++;
    document.getElementById('tool-count').textContent = state.tools;
    const agentId = ev.agent_id || 'main';
    if (!state.agents[agentId]) state.agents[agentId] = { name: agentId === 'main' ? 'Agent principal' : agentId, status: 'working' };
    state.agents[agentId].status = 'working';
    state.agents[agentId].currentTool = ev.tool;
    updateAgentList();
  }

  if (ev.type === 'post_tool') {
    const agentId = ev.agent_id || 'main';
    if (state.agents[agentId]) state.agents[agentId].currentTool = null;
    updateAgentList();
  }

  if (ev.type === 'stop') {
    const badge = document.getElementById('global-status');
    badge.className = 'status-badge idle';
    document.getElementById('status-text').textContent = 'Terminé';
    document.getElementById('pulse-dot').classList.remove('anim');
    Object.values(state.agents).forEach(a => a.status = 'done');
    updateAgentList();
  }
}

// SSE
function connect() {
  const es = new EventSource('/stream');
  const connStatus = document.getElementById('conn-status');

  es.onopen = () => { connStatus.textContent = '⚡ Connexion SSE active'; connStatus.style.color = 'var(--green)'; };
  es.onmessage = (e) => {
    try { processEvent(JSON.parse(e.data)); } catch(err) {}
  };
  es.onerror = () => {
    connStatus.textContent = '⚠️ Reconnexion...'; connStatus.style.color = 'var(--yellow)';
    es.close();
    setTimeout(connect, 3000);
  };
}
connect();
</script>
</body>
</html>"""

# ─── Serveur HTTP ──────────────────────────────────────────────
class MonitorHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Silencieux

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode())

        elif self.path == '/stream':
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            with lock:
                client = self.wfile
                sse_clients.append(client)
                # Envoyer l'historique récent
                for ev in list(events)[-20:]:
                    try:
                        data = f"data: {json.dumps(ev)}\n\n"
                        client.write(data.encode())
                    except:
                        pass

            try:
                while True:
                    time.sleep(15)
                    try:
                        self.wfile.write(b": ping\n\n")
                        self.wfile.flush()
                    except:
                        break
            finally:
                with lock:
                    if client in sse_clients:
                        sse_clients.remove(client)

        elif self.path == '/status':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "events": len(events)}).encode())

    def do_POST(self):
        if self.path == '/event':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                ev = json.loads(body)
                ev['timestamp'] = ev.get('timestamp', time.time())
                with lock:
                    events.append(ev)
                    dead = []
                    for client in sse_clients:
                        try:
                            data = f"data: {json.dumps(ev)}\n\n"
                            client.write(data.encode())
                            client.flush()
                        except:
                            dead.append(client)
                    for d in dead:
                        sse_clients.remove(d)
            except Exception as e:
                print(f"Erreur parsing event: {e}")

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.end_headers()


if __name__ == '__main__':
    port = 7777
    server = HTTPServer(('0.0.0.0', port), MonitorHandler)
    print(f"🔍 Agent Monitor démarré → http://localhost:{port}")
    print("   En attente d'événements Claude Code...")
    print("   Ctrl+C pour arrêter\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nMonitor arrêté.")
