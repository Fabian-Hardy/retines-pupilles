from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


TASK_PATTERN = re.compile(r"\bTASK[-_\s]?(\d{1,4})\b", re.IGNORECASE)


def extract_task_id(text: str) -> str | None:
    match = TASK_PATTERN.search(text or "")
    if not match:
        return None

    return f"TASK-{int(match.group(1)):03d}"


def normalize_pull_request(raw: dict[str, Any]) -> dict[str, Any]:
    number = int(raw.get("number", 0))
    title = str(raw.get("title") or f"Pull request #{number}")
    merged_at = str(raw.get("merged_at") or raw.get("mergedAt") or "")
    html_url = str(raw.get("html_url") or raw.get("url") or "#")
    user = raw.get("user") or {}
    author = str(user.get("login") or raw.get("author") or "unknown")

    return {
        "number": number,
        "title": title,
        "task_id": extract_task_id(title),
        "merged_at": merged_at,
        "html_url": html_url,
        "author": author,
    }


def normalize_roadmap_item(raw: dict[str, Any]) -> dict[str, str]:
    task_id = str(raw.get("id") or raw.get("task_id") or "").strip().upper()
    if not task_id:
        raise ValueError("Each roadmap item must define an id, for example TASK-008.")

    extracted = extract_task_id(task_id)
    if not extracted:
        raise ValueError(f"Invalid roadmap task id: {task_id}")

    return {
        "id": extracted,
        "title": str(raw.get("title") or extracted),
        "phase": str(raw.get("phase") or "Unclassified"),
        "description": str(raw.get("description") or ""),
    }


def load_pull_requests_from_file(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, list):
        raise ValueError("The input JSON file must contain a list of pull requests.")

    return [normalize_pull_request(item) for item in payload]


def load_roadmap_from_file(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open(encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, list):
        raise ValueError("The roadmap JSON file must contain a list of tasks.")

    return [normalize_roadmap_item(item) for item in payload]


def fetch_merged_pull_requests(
    *,
    repo: str,
    base: str,
    token: str,
    limit: int,
) -> list[dict[str, Any]]:
    pull_requests: list[dict[str, Any]] = []
    page = 1

    while len(pull_requests) < limit:
        api_url = (
            f"https://api.github.com/repos/{repo}/pulls"
            f"?state=closed&base={base}&sort=updated&direction=desc"
            f"&per_page=100&page={page}"
        )

        request = Request(
            api_url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "retines-pupilles-progress-page",
            },
        )

        try:
            with urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            raise RuntimeError(
                f"GitHub API request failed with status {error.code}: {error.reason}"
            ) from error
        except URLError as error:
            raise RuntimeError(f"GitHub API request failed: {error.reason}") from error

        if not payload:
            break

        for item in payload:
            if item.get("merged_at"):
                pull_requests.append(normalize_pull_request(item))

            if len(pull_requests) >= limit:
                break

        page += 1

    return pull_requests


def format_date(value: str) -> str:
    if not value:
        return "Unknown date"

    normalized = value.replace("Z", "+00:00")

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return value

    return parsed.strftime("%Y-%m-%d %H:%M UTC")


def sort_key_for_task(task_id: str) -> int:
    match = TASK_PATTERN.search(task_id)
    if not match:
        return 999999
    return int(match.group(1))


def build_task_rows(
    *,
    roadmap: list[dict[str, str]],
    pull_requests: list[dict[str, Any]],
) -> tuple[str, int, int]:
    pr_by_task = {
        item["task_id"]: item
        for item in pull_requests
        if item.get("task_id")
    }

    tasks_by_id = {item["id"]: item for item in roadmap}

    for pr in pull_requests:
        task_id = pr.get("task_id")
        if task_id and task_id not in tasks_by_id:
            tasks_by_id[task_id] = {
                "id": task_id,
                "title": pr["title"],
                "phase": "Merged PR",
                "description": "Detected from merged pull requests.",
            }

    rows = []
    done_count = 0

    for task_id in sorted(tasks_by_id, key=sort_key_for_task):
        task = tasks_by_id[task_id]
        pr = pr_by_task.get(task_id)
        is_done = pr is not None

        if is_done:
            done_count += 1

        status_label = "Terminee" if is_done else "A faire"
        status_class = "done" if is_done else "todo"
        pr_cell = (
            f'<a href="{escape(pr["html_url"])}">#{pr["number"]}</a>'
            if pr
            else "-"
        )
        merged_at = format_date(pr["merged_at"]) if pr else "-"

        rows.append(
            f"""
            <tr>
              <td><span class="badge">{escape(task_id)}</span></td>
              <td><span class="status-pill {status_class}">{status_label}</span></td>
              <td>{escape(task["phase"])}</td>
              <td>
                <strong>{escape(task["title"])}</strong>
                <br />
                <span class="muted">{escape(task["description"])}</span>
              </td>
              <td>{pr_cell}</td>
              <td>{escape(merged_at)}</td>
            </tr>
            """.strip()
        )

    total_count = len(tasks_by_id)
    return "\n".join(rows), done_count, total_count


def build_html(
    pull_requests: list[dict[str, Any]],
    *,
    repo: str,
    base: str,
    roadmap: list[dict[str, str]] | None = None,
    generated_at: datetime | None = None,
) -> str:
    generated_at = generated_at or datetime.now(timezone.utc)
    roadmap = roadmap or []

    latest = max(
        pull_requests,
        key=lambda item: item.get("merged_at") or "",
        default=None,
    )
    task_rows, done_count, total_count = build_task_rows(
        roadmap=roadmap,
        pull_requests=pull_requests,
    )
    todo_count = max(total_count - done_count, 0)
    progress = round((done_count / total_count) * 100) if total_count else 0

    latest_block = (
        f"""
        <a href="{escape(latest["html_url"])}">#{latest["number"]}</a>
        - {escape(latest["title"])}
        <br />
        <span>{escape(format_date(latest["merged_at"]))}</span>
        """.strip()
        if latest
        else "No merged pull request found."
    )

    return f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Retines & Pupilles - Project Progress</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f7fb;
      --panel: #ffffff;
      --text: #18202f;
      --muted: #657084;
      --line: #dfe4ee;
      --accent: #284b8f;
      --accent-soft: #e9eefb;
      --ok: #147a45;
      --todo: #9a5b00;
      --todo-soft: #fff2d8;
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family:
        Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
        "Segoe UI", sans-serif;
      line-height: 1.5;
    }}

    main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 48px 24px;
    }}

    header {{
      margin-bottom: 32px;
    }}

    h1 {{
      margin: 0 0 8px;
      font-size: clamp(2rem, 4vw, 3.25rem);
      letter-spacing: -0.04em;
    }}

    h2 {{
      margin: 0 0 16px;
      font-size: 1.25rem;
    }}

    p {{
      margin: 0;
      color: var(--muted);
    }}

    a {{
      color: var(--accent);
      font-weight: 650;
      text-decoration: none;
    }}

    a:hover {{
      text-decoration: underline;
    }}

    .grid {{
      display: grid;
      gap: 16px;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      margin-bottom: 24px;
    }}

    .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 20px;
      box-shadow: 0 12px 36px rgba(24, 32, 47, 0.06);
    }}

    .metric {{
      display: block;
      margin-top: 8px;
      color: var(--text);
      font-size: 2rem;
      font-weight: 800;
      letter-spacing: -0.04em;
    }}

    .progress-bar {{
      width: 100%;
      height: 14px;
      overflow: hidden;
      border-radius: 999px;
      background: var(--line);
    }}

    .progress-bar span {{
      display: block;
      width: {progress}%;
      height: 100%;
      background: var(--accent);
    }}

    .muted {{
      color: var(--muted);
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      overflow: hidden;
      border-radius: 16px;
    }}

    th,
    td {{
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
    }}

    th {{
      color: var(--muted);
      font-size: 0.8rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}

    tr:last-child td {{
      border-bottom: 0;
    }}

    .badge,
    .status-pill {{
      display: inline-flex;
      border-radius: 999px;
      padding: 4px 10px;
      font-size: 0.85rem;
      font-weight: 750;
      white-space: nowrap;
    }}

    .badge {{
      background: var(--accent-soft);
      color: var(--accent);
    }}

    .status-pill.done {{
      background: #e5f6ed;
      color: var(--ok);
    }}

    .status-pill.todo {{
      background: var(--todo-soft);
      color: var(--todo);
    }}

    .table-card {{
      padding: 0;
      overflow-x: auto;
    }}

    footer {{
      margin-top: 24px;
      color: var(--muted);
      font-size: 0.9rem;
    }}

    @media (max-width: 900px) {{
      .grid {{
        grid-template-columns: 1fr 1fr;
      }}
    }}

    @media (max-width: 640px) {{
      .grid {{
        grid-template-columns: 1fr;
      }}

      main {{
        padding: 32px 16px;
      }}

      th,
      td {{
        padding: 12px;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Retines & Pupilles</h1>
      <p>Avancement du projet - base <strong>{escape(base)}</strong> - depot <strong>{escape(repo)}</strong></p>
    </header>

    <section class="grid" aria-label="Project metrics">
      <article class="card">
        <h2>Progression</h2>
        <span class="metric">{progress}%</span>
        <div class="progress-bar" aria-label="Progression globale">
          <span></span>
        </div>
      </article>

      <article class="card">
        <h2>Taches terminees</h2>
        <span class="metric">{done_count}</span>
      </article>

      <article class="card">
        <h2>Taches restantes</h2>
        <span class="metric">{todo_count}</span>
      </article>

      <article class="card">
        <h2>PR mergees</h2>
        <span class="metric">{len(pull_requests)}</span>
      </article>
    </section>

    <section class="card" style="margin-bottom: 24px;">
      <h2>Derniere PR mergee</h2>
      <p>{latest_block}</p>
    </section>

    <section class="card table-card">
      <table>
        <thead>
          <tr>
            <th>Tache</th>
            <th>Statut</th>
            <th>Phase</th>
            <th>Description</th>
            <th>PR</th>
            <th>Merge</th>
          </tr>
        </thead>
        <tbody>
          {task_rows or '<tr><td colspan="6">Aucune tache trouvee.</td></tr>'}
        </tbody>
      </table>
    </section>

    <footer>
      Page generee automatiquement le {escape(format_date(generated_at.isoformat()))}.
    </footer>
  </main>
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the Retines & Pupilles project progress page."
    )
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY", "Fabian-Hardy/retines-pupilles"))
    parser.add_argument("--base", default="develop")
    parser.add_argument("--output", default="_site/index.html")
    parser.add_argument("--input", help="Read pull requests from a local JSON file instead of GitHub.")
    parser.add_argument("--roadmap", default="docs/project-progress/roadmap.json")
    parser.add_argument("--limit", type=int, default=100)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = Path(args.output)
    roadmap = load_roadmap_from_file(Path(args.roadmap))

    if args.input:
        pull_requests = load_pull_requests_from_file(Path(args.input))
    else:
        token = os.getenv("GITHUB_TOKEN")

        if not token:
            print(
                "GITHUB_TOKEN is required unless --input is provided.",
                file=sys.stderr,
            )
            return 2

        pull_requests = fetch_merged_pull_requests(
            repo=args.repo,
            base=args.base,
            token=token,
            limit=args.limit,
        )

    html = build_html(
        pull_requests,
        repo=args.repo,
        base=args.base,
        roadmap=roadmap,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")

    print(
        f"Generated {output} with {len(pull_requests)} merged pull requests "
        f"and {len(roadmap)} roadmap tasks."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
