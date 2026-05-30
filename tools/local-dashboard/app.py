from __future__ import annotations

import json
import subprocess
from collections import Counter
from datetime import datetime
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


HOST = "127.0.0.1"
PORT = 8787
REPO_ROOT = Path(__file__).resolve().parents[2]
ROADMAP_PATH = REPO_ROOT / "docs" / "project-progress" / "roadmap.json"
RUNS_ROOT = REPO_ROOT / ".local-codex" / "runs"
DONE_STATUSES = {"done", "complete", "completed", "merged", "closed"}


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def run_git(args: list[str], timeout: int = 5) -> tuple[int, str]:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return 1, str(error)

    output = result.stdout.strip() or result.stderr.strip()
    return result.returncode, output


def load_roadmap() -> tuple[list[dict[str, Any]], str | None]:
    if not ROADMAP_PATH.exists():
        return [], f"Missing roadmap file: {ROADMAP_PATH}"

    try:
        payload = read_json(ROADMAP_PATH)
    except (OSError, json.JSONDecodeError) as error:
        return [], f"Could not read roadmap: {error}"

    if not isinstance(payload, list):
        return [], "Roadmap JSON must be a list."

    items = [item for item in payload if isinstance(item, dict)]
    return items, None


def roadmap_metrics(items: list[dict[str, Any]]) -> dict[str, Any]:
    phases = Counter(str(item.get("phase") or "Unclassified") for item in items)
    completed = sum(
        1
        for item in items
        if str(item.get("status") or "").strip().lower() in DONE_STATUSES
    )
    total = len(items)
    percent = round((completed / total) * 100) if total else 0

    return {
        "total": total,
        "completed": completed,
        "remaining": max(total - completed, 0),
        "percent": percent,
        "phases": phases,
        "has_statuses": any("status" in item for item in items),
    }


def load_git_summary() -> dict[str, Any]:
    branch_code, branch = run_git(["branch", "--show-current"])
    status_code, status = run_git(["status", "--short"])
    upstream_code, upstream = run_git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    head_code, head = run_git(["rev-parse", "--short", "HEAD"])

    status_lines = [line for line in status.splitlines() if line.strip()] if status_code == 0 else []

    return {
        "branch": branch if branch_code == 0 and branch else "unknown",
        "head": head if head_code == 0 and head else "unknown",
        "upstream": upstream if upstream_code == 0 and upstream else "none",
        "status_ok": status_code == 0,
        "status_lines": status_lines,
        "status_error": "" if status_code == 0 else status,
    }


def parse_iso(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def format_time(value: str | None) -> str:
    if not value:
        return "-"

    parsed = parse_iso(value)
    if parsed is None:
        return value

    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def load_recent_runs(limit: int = 8) -> list[dict[str, Any]]:
    if not RUNS_ROOT.exists():
        return []

    runs: list[dict[str, Any]] = []
    for run_dir in sorted(RUNS_ROOT.iterdir(), key=lambda path: path.stat().st_mtime, reverse=True):
        if not run_dir.is_dir():
            continue

        metadata_path = run_dir / "run.json"
        if metadata_path.exists():
            try:
                metadata = read_json(metadata_path)
            except (OSError, json.JSONDecodeError):
                metadata = {}
        else:
            metadata = {}

        runs.append(
            {
                "name": run_dir.name,
                "task_id": str(metadata.get("task_id") or "-"),
                "status": str(metadata.get("status") or "unknown"),
                "branch": str(metadata.get("branch") or "-"),
                "started_at": format_time(metadata.get("started_at")),
                "pr_url": str(metadata.get("pr_url") or ""),
            }
        )

        if len(runs) >= limit:
            break

    return runs


def metric_card(label: str, value: str, detail: str = "") -> str:
    detail_html = f"<p>{escape(detail)}</p>" if detail else ""
    return f"""
    <article class="metric">
      <span>{escape(label)}</span>
      <strong>{escape(value)}</strong>
      {detail_html}
    </article>
    """


def build_phase_rows(phases: Counter[str]) -> str:
    if not phases:
        return '<tr><td colspan="2">No roadmap phases found.</td></tr>'

    rows = []
    for phase, count in phases.most_common():
        rows.append(
            "<tr>"
            f"<td>{escape(phase)}</td>"
            f"<td>{count}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def build_task_rows(items: list[dict[str, Any]], limit: int = 12) -> str:
    if not items:
        return '<tr><td colspan="4">No roadmap items found.</td></tr>'

    rows = []
    for item in items[:limit]:
        task_id = str(item.get("id") or item.get("task_id") or "-")
        title = str(item.get("title") or "-")
        phase = str(item.get("phase") or "-")
        status = str(item.get("status") or "planned")
        rows.append(
            "<tr>"
            f"<td><code>{escape(task_id)}</code></td>"
            f"<td>{escape(title)}</td>"
            f"<td>{escape(phase)}</td>"
            f"<td>{escape(status)}</td>"
            "</tr>"
        )

    return "\n".join(rows)


def build_status_block(git: dict[str, Any]) -> str:
    if not git["status_ok"]:
        return f"<pre>{escape(git['status_error'])}</pre>"

    if not git["status_lines"]:
        return "<pre>clean</pre>"

    visible_lines = git["status_lines"][:16]
    suffix = "" if len(git["status_lines"]) <= 16 else "\n..."
    return f"<pre>{escape(chr(10).join(visible_lines) + suffix)}</pre>"


def build_runs_rows(runs: list[dict[str, Any]]) -> str:
    if not runs:
        return '<tr><td colspan="5">No local Codex runs found.</td></tr>'

    rows = []
    for run in runs:
        pr_url = run["pr_url"]
        pr_cell = f'<a href="{escape(pr_url)}">PR</a>' if pr_url else "-"
        rows.append(
            "<tr>"
            f"<td><code>{escape(run['task_id'])}</code></td>"
            f"<td>{escape(run['status'])}</td>"
            f"<td>{escape(run['branch'])}</td>"
            f"<td>{escape(run['started_at'])}</td>"
            f"<td>{pr_cell}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def build_dashboard_html() -> str:
    roadmap, roadmap_error = load_roadmap()
    metrics = roadmap_metrics(roadmap)
    git = load_git_summary()
    runs = load_recent_runs()
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    status_note = (
        "Roadmap status fields detected."
        if metrics["has_statuses"]
        else "Current roadmap items do not include status fields, so completion is shown as 0 until status data is added."
    )
    roadmap_error_html = f'<p class="warning">{escape(roadmap_error)}</p>' if roadmap_error else ""

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Retines & Pupilles Local Automation</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f5f6f8;
      --panel: #ffffff;
      --text: #17202a;
      --muted: #5f6b7a;
      --line: #d8dde5;
      --blue: #255c99;
      --green: #1f7a52;
      --amber: #946200;
      --red: #a33a32;
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }}

    main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}

    header {{
      display: flex;
      flex-wrap: wrap;
      align-items: end;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 24px;
    }}

    h1, h2 {{
      margin: 0;
      letter-spacing: 0;
    }}

    h1 {{ font-size: 2rem; }}
    h2 {{ font-size: 1.1rem; }}

    p {{ margin: 8px 0 0; color: var(--muted); }}
    a {{ color: var(--blue); font-weight: 650; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}

    .grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }}

    .two-col {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 16px;
      margin-bottom: 16px;
    }}

    section, .metric {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }}

    .metric span {{
      display: block;
      color: var(--muted);
      font-size: 0.85rem;
      font-weight: 650;
    }}

    .metric strong {{
      display: block;
      margin-top: 8px;
      font-size: 1.8rem;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 12px;
    }}

    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 10px 8px;
      text-align: left;
      vertical-align: top;
    }}

    th {{
      color: var(--muted);
      font-size: 0.78rem;
      text-transform: uppercase;
    }}

    tr:last-child td {{ border-bottom: 0; }}

    code, pre {{
      font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
      font-size: 0.9rem;
    }}

    pre {{
      overflow-x: auto;
      margin: 12px 0 0;
      padding: 12px;
      background: #101820;
      color: #ecf2f8;
      border-radius: 6px;
    }}

    .progress {{
      width: 100%;
      height: 12px;
      margin-top: 12px;
      overflow: hidden;
      background: #e5e9ef;
      border-radius: 999px;
    }}

    .progress span {{
      display: block;
      width: {metrics["percent"]}%;
      height: 100%;
      background: var(--green);
    }}

    .warning {{ color: var(--red); }}
    .commands p {{ color: var(--text); }}
    .footer {{ color: var(--muted); font-size: 0.85rem; margin-top: 16px; }}

    @media (max-width: 900px) {{
      .grid, .two-col {{ grid-template-columns: 1fr; }}
      main {{ padding: 24px 12px; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>Local Automation</h1>
        <p>Read-only localhost dashboard for TOOL-001.</p>
      </div>
      <p>Generated {escape(generated_at)}</p>
    </header>

    <div class="grid">
      {metric_card("Roadmap items", str(metrics["total"]), "Loaded from docs/project-progress/roadmap.json")}
      {metric_card("Completed", str(metrics["completed"]), status_note)}
      {metric_card("Remaining", str(metrics["remaining"]))}
      {metric_card("Branch", str(git["branch"]), f"HEAD {git['head']}")}
    </div>

    <section style="margin-bottom: 16px;">
      <h2>Roadmap Progress</h2>
      {roadmap_error_html}
      <div class="progress" aria-label="Roadmap completion"><span></span></div>
      <table>
        <thead><tr><th>Phase</th><th>Items</th></tr></thead>
        <tbody>{build_phase_rows(metrics["phases"])}</tbody>
      </table>
    </section>

    <div class="two-col">
      <section>
        <h2>Git Status</h2>
        <p>Upstream: {escape(str(git["upstream"]))}</p>
        {build_status_block(git)}
      </section>

      <section class="commands">
        <h2>Quick Commands</h2>
        <p><code>python tools\\local-dashboard\\app.py</code></p>
        <p><code>.\\tools\\local-codex-runner.ps1 status</code></p>
        <p><code>.\\tools\\local-codex-runner.ps1 run-task _tasks\\tool-001-local-automation.md -TaskId TOOL-001</code></p>
        <p><code>git diff --check</code></p>
      </section>
    </div>

    <section style="margin-bottom: 16px;">
      <h2>Recent Local Runs</h2>
      <table>
        <thead><tr><th>Task</th><th>Status</th><th>Branch</th><th>Started</th><th>PR</th></tr></thead>
        <tbody>{build_runs_rows(runs)}</tbody>
      </table>
    </section>

    <section>
      <h2>Roadmap Preview</h2>
      <table>
        <thead><tr><th>Id</th><th>Title</th><th>Phase</th><th>Status</th></tr></thead>
        <tbody>{build_task_rows(roadmap)}</tbody>
      </table>
    </section>

    <p class="footer">This dashboard binds to 127.0.0.1:{PORT} and has no endpoint for arbitrary command execution.</p>
  </main>
</body>
</html>"""


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "RetinesLocalDashboard/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/healthz":
            self.send_json({"ok": True})
            return

        if parsed.path != "/":
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        html = build_dashboard_html().encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(html)

    def send_json(self, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{timestamp} {self.address_string()} {format % args}")


def main() -> int:
    server = ThreadingHTTPServer((HOST, PORT), DashboardHandler)
    print(f"Serving Retines & Pupilles local dashboard at http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("")
        print("Stopping dashboard.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
