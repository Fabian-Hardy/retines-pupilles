# Local Dashboard

TOOL-001 adds a small localhost-only dashboard for local automation status.

Run it from the repository root:

```powershell
python tools\local-dashboard\app.py
```

Open:

```text
http://127.0.0.1:8787
```

The dashboard uses only the Python standard library. It binds to `127.0.0.1`,
reads `docs/project-progress/roadmap.json`, shows a fixed `git` status summary,
lists recent `.local-codex/runs` metadata, and displays quick commands.

It does not expose an endpoint that accepts or executes arbitrary commands.
