from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_NAME = "Fabian-Hardy/retines-pupilles"
DEFAULT_BASE_BRANCH = "develop"
DEFAULT_STATE_DIR = Path(".local/agentic-control-plane")
DEFAULT_QUEUE_CANDIDATES = (
    Path("docs/agent-queue/issues-batch-01.json"),
    Path("_tasks/chain-sprint-1.json"),
)

STATUSES = (
    "pending",
    "running",
    "failed",
    "pr_open",
    "ci_pending",
    "ready_to_merge",
    "merged",
    "skipped",
    "needs_human",
)
TERMINAL_STATUSES = {"failed", "merged", "skipped", "needs_human"}
RISK_LEVELS = {"low", "medium", "high"}
TASK_ID_PATTERN = re.compile(r"\b(?:TASK|TOOL)[-_\s]?(\d{1,4})\b", re.IGNORECASE)

VALIDATION_PRESETS = {
    "backend": [
        "cd backend && source ../.venv/bin/activate && set -a && source .env && "
        "set +a && ruff check . && mypy . && pytest"
    ],
    "frontend": ["cd frontend && npm ci && npm run typecheck && npm run build"],
    "docs": ["git diff --check"],
    "tooling": [
        "git diff --check",
        "python -m unittest tests.tools.test_agentic_control_plane",
    ],
}

SECRET_LINE_PATTERN = re.compile(
    r"(?i)(api[_-]?key|secret|token|password|private[_-]?key)\s*[:=]\s*"
    r"['\"]?[A-Za-z0-9_./+=-]{8,}"
)
DESTRUCTIVE_MIGRATION_PATTERN = re.compile(
    r"(?i)(op\.drop_(table|column)|drop\s+table|drop\s+column|truncate\s+table|delete\s+from)"
)


@dataclass(frozen=True)
class CommandResult:
    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and self.error is None


@dataclass(frozen=True)
class QueueEntry:
    id: str
    title: str
    branch: str
    status: str
    depends_on: tuple[str, ...]
    risk_level: str
    allow_auto_merge: bool
    validation_commands: tuple[str, ...]
    notes: tuple[str, ...]
    files: tuple[str, ...] = ()
    task_file: str | None = None
    version: str | None = None
    task_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "branch": self.branch,
            "status": self.status,
            "depends_on": list(self.depends_on),
            "risk_level": self.risk_level,
            "allow_auto_merge": self.allow_auto_merge,
            "validation_commands": list(self.validation_commands),
            "notes": list(self.notes),
            "files": list(self.files),
            "task_file": self.task_file,
            "version": self.version,
            "type": self.task_type,
        }


@dataclass(frozen=True)
class PolicyCheck:
    name: str
    passed: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


@dataclass(frozen=True)
class PolicyDecision:
    mergeable: bool
    status: str
    checks: tuple[PolicyCheck, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "mergeable": self.mergeable,
            "status": self.status,
            "checks": [check.to_dict() for check in self.checks],
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_task_id(value: Any) -> str:
    text = str(value or "").strip().upper()
    if not text:
        raise ValueError("Queue entry is missing an id.")

    match = TASK_ID_PATTERN.search(text)
    if not match:
        raise ValueError(f"Invalid task id: {text}")

    prefix = "TOOL" if "TOOL" in match.group(0).upper() else "TASK"
    return f"{prefix}-{int(match.group(1)):03d}"


def normalize_string_list(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        stripped = value.strip()
        return (stripped,) if stripped else ()
    if isinstance(value, list):
        return tuple(str(item).strip() for item in value if str(item).strip())
    raise ValueError(f"Expected a string or list of strings, got {type(value).__name__}.")


def normalize_bool(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    raise ValueError(f"Expected a boolean value, got {value!r}.")


def normalize_validation_commands(raw: dict[str, Any]) -> tuple[str, ...]:
    explicit = raw.get("validation_commands")
    if explicit is not None:
        return normalize_string_list(explicit)

    validations = raw.get("validations")
    if isinstance(validations, list):
        commands = []
        for item in validations:
            if isinstance(item, dict) and item.get("command"):
                commands.append(str(item["command"]).strip())
            elif isinstance(item, str):
                commands.append(item.strip())
        return tuple(command for command in commands if command)

    preset = raw.get("validation")
    if preset is None:
        return ()

    preset_key = str(preset).strip().lower()
    if preset_key in VALIDATION_PRESETS:
        return tuple(VALIDATION_PRESETS[preset_key])
    return normalize_string_list(preset)


def normalize_queue_entry(raw: dict[str, Any]) -> QueueEntry:
    task_id = normalize_task_id(raw.get("id") or raw.get("task_id") or raw.get("task"))
    title = str(raw.get("title") or task_id).strip()
    branch = str(raw.get("branch") or raw.get("branchName") or f"codex/{task_id.lower()}").strip()
    status = str(raw.get("status") or "pending").strip().lower()
    depends_on = normalize_string_list(
        raw.get("depends_on") if "depends_on" in raw else raw.get("dependencies")
    )
    risk_level = str(raw.get("risk_level") or raw.get("risk") or "medium").strip().lower()
    notes = normalize_string_list(raw.get("notes"))
    files = normalize_string_list(raw.get("files"))
    task_file = raw.get("taskFile") or raw.get("task_file")

    return QueueEntry(
        id=task_id,
        title=title,
        branch=branch,
        status=status,
        depends_on=tuple(normalize_task_id(item) for item in depends_on),
        risk_level=risk_level,
        allow_auto_merge=normalize_bool(raw.get("allow_auto_merge"), default=False),
        validation_commands=normalize_validation_commands(raw),
        notes=notes,
        files=files,
        task_file=str(task_file).strip() if task_file else None,
        version=str(raw.get("version")).strip() if raw.get("version") else None,
        task_type=str(raw.get("type")).strip() if raw.get("type") else None,
    )


def find_queue_file(repo_root: Path, explicit_path: Path | None = None) -> Path:
    if explicit_path is not None:
        path = explicit_path if explicit_path.is_absolute() else repo_root / explicit_path
        if not path.exists():
            raise FileNotFoundError(f"Queue file does not exist: {path}")
        return path

    for candidate in DEFAULT_QUEUE_CANDIDATES:
        path = repo_root / candidate
        if path.exists():
            return path

    raise FileNotFoundError(
        "No queue file found. Expected one of: "
        + ", ".join(str(path) for path in DEFAULT_QUEUE_CANDIDATES)
    )


def load_queue(path: Path) -> list[QueueEntry]:
    with path.open(encoding="utf-8") as file:
        payload = json.load(file)

    if isinstance(payload, list):
        raw_entries = payload
    elif isinstance(payload, dict) and isinstance(payload.get("tasks"), list):
        raw_entries = payload["tasks"]
    elif isinstance(payload, dict) and isinstance(payload.get("queue"), list):
        raw_entries = payload["queue"]
    else:
        raise ValueError("Queue JSON must be a list or an object with a tasks/queue list.")

    entries = []
    for raw in raw_entries:
        if not isinstance(raw, dict):
            raise ValueError("Each queue entry must be a JSON object.")
        entries.append(normalize_queue_entry(raw))
    return entries


def validate_queue_entries(entries: list[QueueEntry]) -> list[str]:
    errors = []
    seen_ids: set[str] = set()
    for entry in entries:
        if entry.id in seen_ids:
            errors.append(f"{entry.id}: duplicate task id")
        seen_ids.add(entry.id)

        if not entry.title:
            errors.append(f"{entry.id}: title is required")
        if not entry.branch:
            errors.append(f"{entry.id}: branch is required")
        if entry.branch in {"main", "develop"}:
            errors.append(f"{entry.id}: branch must not be {entry.branch}")
        if entry.status not in STATUSES:
            errors.append(f"{entry.id}: unsupported status {entry.status}")
        if entry.risk_level not in RISK_LEVELS:
            errors.append(f"{entry.id}: unsupported risk_level {entry.risk_level}")
        if not isinstance(entry.allow_auto_merge, bool):
            errors.append(f"{entry.id}: allow_auto_merge must be a boolean")
    return errors


def slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "task"


class StateStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.tasks_dir = self.root / "tasks"
        self.runs_dir = self.root / "runs"

    def initialize(self) -> None:
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def task_path(self, task_id: str) -> Path:
        return self.tasks_dir / f"{normalize_task_id(task_id)}.json"

    def load_task(self, task_id: str) -> dict[str, Any] | None:
        path = self.task_path(task_id)
        if not path.exists():
            return None
        with path.open(encoding="utf-8") as file:
            payload = json.load(file)
        if not isinstance(payload, dict):
            raise ValueError(f"Task state must be a JSON object: {path}")
        return payload

    def list_tasks(self) -> list[dict[str, Any]]:
        if not self.tasks_dir.exists():
            return []

        states = []
        for path in sorted(self.tasks_dir.glob("*.json")):
            with path.open(encoding="utf-8") as file:
                payload = json.load(file)
            if isinstance(payload, dict):
                states.append(payload)
        return states

    def validate(self) -> list[str]:
        errors = []
        if not self.tasks_dir.exists():
            return errors

        for path in sorted(self.tasks_dir.glob("*.json")):
            try:
                with path.open(encoding="utf-8") as file:
                    payload = json.load(file)
            except json.JSONDecodeError as error:
                errors.append(f"{path}: invalid JSON: {error}")
                continue

            if not isinstance(payload, dict):
                errors.append(f"{path}: state must be a JSON object")
                continue

            task_id = payload.get("task_id")
            status = payload.get("status")
            if not task_id:
                errors.append(f"{path}: missing task_id")
            else:
                try:
                    normalize_task_id(task_id)
                except ValueError as error:
                    errors.append(f"{path}: {error}")
            if status not in STATUSES:
                errors.append(f"{path}: unsupported status {status}")
        return errors

    def default_log_paths(self, task_id: str) -> dict[str, str]:
        run_dir = self.runs_dir / slug(normalize_task_id(task_id))
        return {
            "stdout": str(run_dir / "stdout.log"),
            "stderr": str(run_dir / "stderr.log"),
            "codex": str(run_dir / "codex.log"),
            "run_json": str(run_dir / "run.json"),
        }

    def mark_task(
        self,
        task_id: str,
        *,
        status: str,
        branch: str,
        pr_number: int | None = None,
        last_error: str | None = None,
        validation_results: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        task_id = normalize_task_id(task_id)
        if status not in STATUSES:
            raise ValueError(f"Unsupported status {status}. Expected one of: {', '.join(STATUSES)}")

        self.initialize()
        now = utc_now()
        existing = self.load_task(task_id) or {}
        timestamps = existing.get("timestamps") if isinstance(existing.get("timestamps"), dict) else {}
        timestamps.setdefault("created_at", now)
        timestamps["updated_at"] = now

        if status == "running" and not timestamps.get("started_at"):
            timestamps["started_at"] = now
        if status in TERMINAL_STATUSES and not timestamps.get("completed_at"):
            timestamps["completed_at"] = now

        state = {
            "task_id": task_id,
            "status": status,
            "branch": branch,
            "pr_number": pr_number if pr_number is not None else existing.get("pr_number"),
            "timestamps": timestamps,
            "last_error": last_error if last_error is not None else existing.get("last_error"),
            "validation_results": validation_results
            if validation_results is not None
            else existing.get("validation_results", []),
            "log_paths": existing.get("log_paths") or self.default_log_paths(task_id),
        }

        path = self.task_path(task_id)
        with path.open("w", encoding="utf-8") as file:
            json.dump(state, file, indent=2, sort_keys=True)
            file.write("\n")
        return state


def state_by_task_id(store: StateStore) -> dict[str, dict[str, Any]]:
    return {
        normalize_task_id(state["task_id"]): state
        for state in store.list_tasks()
        if state.get("task_id")
    }


def effective_status(entry: QueueEntry, states: dict[str, dict[str, Any]]) -> str:
    state = states.get(entry.id)
    if state and state.get("status") in STATUSES:
        return str(state["status"])
    return entry.status


def dependency_is_satisfied(task_id: str, entries: dict[str, QueueEntry], states: dict[str, Any]) -> bool:
    state = states.get(task_id)
    if state and state.get("status") == "merged":
        return True
    entry = entries.get(task_id)
    return bool(entry and entry.status == "merged")


def find_next_task(entries: list[QueueEntry], store: StateStore) -> QueueEntry | None:
    entries_by_id = {entry.id: entry for entry in entries}
    states = state_by_task_id(store)

    for entry in entries:
        if effective_status(entry, states) != "pending":
            continue
        if all(dependency_is_satisfied(dep, entries_by_id, states) for dep in entry.depends_on):
            return entry
    return None


def run_command(args: list[str], cwd: Path, timeout: int = 20) -> CommandResult:
    try:
        completed = subprocess.run(
            args,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as error:
        return CommandResult(tuple(args), 127, "", "", str(error))
    except subprocess.TimeoutExpired as error:
        return CommandResult(tuple(args), 124, error.stdout or "", error.stderr or "", "timeout")

    return CommandResult(tuple(args), completed.returncode, completed.stdout, completed.stderr)


def get_current_branch(repo_root: Path) -> dict[str, Any]:
    result = run_command(["git", "branch", "--show-current"], repo_root)
    return {
        "ok": result.ok,
        "branch": result.stdout.strip() if result.ok else None,
        "error": result.stderr.strip() or result.error,
    }


def get_working_tree_status(repo_root: Path) -> dict[str, Any]:
    result = run_command(["git", "status", "--porcelain"], repo_root)
    lines = [line for line in result.stdout.splitlines() if line.strip()] if result.ok else []
    return {
        "ok": result.ok,
        "clean": result.ok and not lines,
        "changes": lines,
        "error": result.stderr.strip() or result.error,
    }


def local_branch_exists(repo_root: Path, branch: str) -> dict[str, Any]:
    result = run_command(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"], repo_root)
    return {"ok": result.returncode in {0, 1}, "exists": result.returncode == 0, "error": result.error}


def remote_branch_exists(repo_root: Path, branch: str) -> dict[str, Any]:
    result = run_command(
        ["git", "show-ref", "--verify", "--quiet", f"refs/remotes/origin/{branch}"], repo_root
    )
    return {"ok": result.returncode in {0, 1}, "exists": result.returncode == 0, "error": result.error}


def existing_pr_for_branch(repo_root: Path, repo: str, branch: str) -> dict[str, Any]:
    if shutil.which("gh") is None:
        return {"ok": False, "available": False, "pr": None, "error": "gh CLI is not available"}

    result = run_command(
        [
            "gh",
            "pr",
            "view",
            "--repo",
            repo,
            "--head",
            branch,
            "--json",
            "number,url,isDraft,state,headRefName,baseRefName",
        ],
        repo_root,
        timeout=30,
    )
    if not result.ok:
        return {
            "ok": True,
            "available": True,
            "pr": None,
            "error": result.stderr.strip() or result.stdout.strip() or result.error,
        }

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        return {"ok": False, "available": True, "pr": None, "error": f"Invalid gh JSON: {error}"}

    return {"ok": True, "available": True, "pr": payload, "error": None}


def inspect_git_and_github(repo_root: Path, branch: str, repo: str) -> dict[str, Any]:
    return {
        "current_branch": get_current_branch(repo_root),
        "working_tree": get_working_tree_status(repo_root),
        "local_branch": local_branch_exists(repo_root, branch),
        "remote_branch": remote_branch_exists(repo_root, branch),
        "pull_request": existing_pr_for_branch(repo_root, repo, branch),
    }


def path_matches_scope(path: str, scope: str) -> bool:
    normalized_path = path.replace("\\", "/").strip("/")
    normalized_scope = scope.replace("\\", "/").strip("/")
    if not normalized_scope:
        return False
    if normalized_scope.endswith("*"):
        return normalized_path.startswith(normalized_scope[:-1])
    if normalized_path == normalized_scope:
        return True
    return normalized_path.startswith(f"{normalized_scope.rstrip('/')}/")


def is_diff_scoped_to_task(entry: QueueEntry, changed_files: tuple[str, ...]) -> bool:
    if not changed_files or not entry.files:
        return False
    return all(any(path_matches_scope(path, scope) for scope in entry.files) for path in changed_files)


def secrets_detected(changed_files: tuple[str, ...], diff_text: str) -> bool:
    for path in changed_files:
        normalized = path.replace("\\", "/").lower()
        name = Path(normalized).name
        if name == ".env" or name.endswith(".pem") or name in {"id_rsa", "id_dsa"}:
            return True
        if "/secrets/" in normalized or "/credentials/" in normalized:
            return True

    for line in diff_text.splitlines():
        if line.startswith("+") and not line.startswith("+++") and SECRET_LINE_PATTERN.search(line):
            return True
    return False


def destructive_migration_detected(changed_files: tuple[str, ...], diff_text: str) -> bool:
    touches_migration = any("alembic/versions/" in path.replace("\\", "/") for path in changed_files)
    if not touches_migration:
        return False
    return any(
        line.startswith("+")
        and not line.startswith("+++")
        and DESTRUCTIVE_MIGRATION_PATTERN.search(line)
        for line in diff_text.splitlines()
    )


def sensitive_infra_or_prod_changes_detected(changed_files: tuple[str, ...]) -> bool:
    sensitive_paths = (
        ".github/workflows/",
        "docker-compose.prod.yml",
        "traefik/",
        "docs/deploy/",
        "deploy/",
        "infra/",
    )
    for path in changed_files:
        normalized = path.replace("\\", "/").lstrip("/")
        if any(normalized == scope.rstrip("/") or normalized.startswith(scope) for scope in sensitive_paths):
            return True
    return False


def major_ux_or_business_rule_change_detected(changed_files: tuple[str, ...]) -> bool:
    product_paths = ("backend/app/", "frontend/src/")
    test_paths = ("backend/tests/", "tests/")
    for path in changed_files:
        normalized = path.replace("\\", "/").lstrip("/")
        if normalized.startswith(test_paths):
            continue
        if normalized.startswith(product_paths):
            return True
    return False


def evaluate_merge_policy(
    entry: QueueEntry,
    *,
    pr_is_draft: bool,
    ci_green: bool,
    changed_files: tuple[str, ...],
    diff_text: str = "",
    diff_scoped: bool | None = None,
    has_secrets: bool | None = None,
    has_destructive_migration: bool | None = None,
    has_sensitive_infra_or_prod_changes: bool | None = None,
    has_major_ux_or_business_rule_change: bool | None = None,
) -> PolicyDecision:
    scoped = diff_scoped if diff_scoped is not None else is_diff_scoped_to_task(entry, changed_files)
    secret_flag = has_secrets if has_secrets is not None else secrets_detected(changed_files, diff_text)
    migration_flag = (
        has_destructive_migration
        if has_destructive_migration is not None
        else destructive_migration_detected(changed_files, diff_text)
    )
    infra_flag = (
        has_sensitive_infra_or_prod_changes
        if has_sensitive_infra_or_prod_changes is not None
        else sensitive_infra_or_prod_changes_detected(changed_files)
    )
    business_flag = (
        has_major_ux_or_business_rule_change
        if has_major_ux_or_business_rule_change is not None
        else major_ux_or_business_rule_change_detected(changed_files)
    )

    checks = (
        PolicyCheck("pr_not_draft", not pr_is_draft, "PR must not be draft."),
        PolicyCheck("ci_green", ci_green, "CI must be green."),
        PolicyCheck("diff_scoped_to_task", scoped, "Changed files must match the task scope."),
        PolicyCheck("no_secrets_detected", not secret_flag, "No secrets may be detected."),
        PolicyCheck(
            "no_destructive_migration",
            not migration_flag,
            "Destructive migrations are not auto-merge candidates.",
        ),
        PolicyCheck(
            "no_sensitive_infra_or_prod_changes",
            not infra_flag,
            "Sensitive infrastructure or production changes require human review.",
        ),
        PolicyCheck(
            "no_major_ux_or_business_rule_change",
            not business_flag,
            "Major UX or business-rule changes require human review.",
        ),
        PolicyCheck(
            "allow_auto_merge",
            entry.allow_auto_merge,
            "Queue entry must explicitly allow auto-merge.",
        ),
        PolicyCheck("risk_level_low", entry.risk_level == "low", "Queue entry risk_level must be low."),
    )

    mergeable = all(check.passed for check in checks)
    return PolicyDecision(
        mergeable=mergeable,
        status="ready_to_merge" if mergeable else "needs_human",
        checks=checks,
    )


def resolve_paths(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    repo_root = Path(args.repo_root).resolve()
    queue_file = find_queue_file(repo_root, Path(args.queue_file) if args.queue_file else None)
    state_dir = Path(args.state_dir)
    if not state_dir.is_absolute():
        state_dir = repo_root / state_dir
    return repo_root, queue_file, state_dir


def print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def command_init(args: argparse.Namespace) -> int:
    repo_root, queue_file, state_dir = resolve_paths(args)
    store = StateStore(state_dir)
    store.initialize()

    print(f"Initialized local control-plane state: {state_dir}")
    print(f"Queue file: {queue_file.relative_to(repo_root)}")
    print("No git, GitHub, merge, deployment, or Codex execution actions were performed.")
    return 0


def command_queue(args: argparse.Namespace) -> int:
    repo_root, queue_file, state_dir = resolve_paths(args)
    entries = load_queue(queue_file)
    states = state_by_task_id(StateStore(state_dir))

    filtered = []
    for entry in entries:
        status = effective_status(entry, states)
        if args.status and status != args.status:
            continue
        payload = entry.to_dict()
        payload["status"] = status
        filtered.append(payload)

    if args.json:
        print_json(filtered)
        return 0

    print(f"Queue: {queue_file.relative_to(repo_root)}")
    for entry in filtered:
        deps = ",".join(entry["depends_on"]) or "-"
        print(
            f"{entry['id']:9} {entry['status']:14} {entry['risk_level']:6} "
            f"{entry['branch']} deps={deps} title={entry['title']}"
        )
    return 0


def command_status(args: argparse.Namespace) -> int:
    repo_root, queue_file, state_dir = resolve_paths(args)
    store = StateStore(state_dir)
    branch = get_current_branch(repo_root)
    tree = get_working_tree_status(repo_root)

    if args.json:
        print_json(
            {
                "queue_file": str(queue_file),
                "state_dir": str(state_dir),
                "current_branch": branch,
                "working_tree": tree,
                "tasks": store.list_tasks(),
            }
        )
        return 0

    print(f"Queue file: {queue_file.relative_to(repo_root)}")
    print(f"State dir: {state_dir}")
    print(f"Current branch: {branch.get('branch') or 'unknown'}")
    print("Working tree: clean" if tree.get("clean") else "Working tree: dirty or unavailable")
    if tree.get("changes"):
        for change in tree["changes"]:
            print(f"  {change}")

    states = store.list_tasks()
    print("")
    print("Task state:")
    if not states:
        print("  none")
    for state in states:
        pr = state.get("pr_number")
        pr_text = f" PR #{pr}" if pr else ""
        print(f"  {state.get('task_id')} {state.get('status')} {state.get('branch')}{pr_text}")
    return 0


def command_next(args: argparse.Namespace) -> int:
    repo_root, queue_file, state_dir = resolve_paths(args)
    entry = find_next_task(load_queue(queue_file), StateStore(state_dir))

    if args.json:
        print_json(entry.to_dict() if entry else None)
        return 0

    if entry is None:
        print("No pending task is currently unblocked.")
        return 1

    print(f"Next task: {entry.id} - {entry.title}")
    print(f"Branch: {entry.branch}")
    print(f"Risk: {entry.risk_level}")
    print("Validation commands:")
    for command in entry.validation_commands:
        print(f"  {command}")
    return 0


def command_run(args: argparse.Namespace) -> int:
    repo_root, queue_file, state_dir = resolve_paths(args)
    entries = load_queue(queue_file)
    store = StateStore(state_dir)

    if args.task_id:
        normalized = normalize_task_id(args.task_id)
        entry = next((item for item in entries if item.id == normalized), None)
        if entry is None:
            print(f"Task not found in queue: {normalized}", file=sys.stderr)
            return 1
    else:
        entry = find_next_task(entries, store)
        if entry is None:
            print("No pending task is currently unblocked.", file=sys.stderr)
            return 1

    if not args.dry_run:
        print(
            "Refusing to run without --dry-run. TOOL-005 only reports planned actions; "
            "Codex execution, commits, pushes, PR creation, and merges are not implemented here.",
            file=sys.stderr,
        )
        return 2

    inspection = inspect_git_and_github(repo_root, entry.branch, args.repo)

    print(f"Dry-run for {entry.id}: {entry.title}")
    print(f"Queue file: {queue_file.relative_to(repo_root)}")
    print(f"State dir: {state_dir}")
    print("")
    print("Inspection:")
    print(f"  current_branch: {inspection['current_branch'].get('branch') or 'unknown'}")
    print(f"  working_tree_clean: {inspection['working_tree'].get('clean')}")
    print(f"  local_branch_exists: {inspection['local_branch'].get('exists')}")
    print(f"  remote_branch_exists: {inspection['remote_branch'].get('exists')}")
    pr = inspection["pull_request"].get("pr")
    print(f"  existing_pr: #{pr['number']} {pr['url']}" if pr else "  existing_pr: none")
    print("")
    print("Planned actions only:")
    print(f"  1. Prepare branch {entry.branch} from {DEFAULT_BASE_BRANCH}.")
    print("  2. Run local Codex for the task prompt.")
    for index, command in enumerate(entry.validation_commands, start=3):
        print(f"  {index}. Validate: {command}")
    print("  N. Report policy readiness only. No merge will be performed.")
    return 0


def command_validate(args: argparse.Namespace) -> int:
    _, queue_file, state_dir = resolve_paths(args)
    queue_errors = validate_queue_entries(load_queue(queue_file))
    state_errors = StateStore(state_dir).validate()
    errors = queue_errors + state_errors

    if args.json:
        print_json({"ok": not errors, "errors": errors})
        return 0 if not errors else 1

    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("Control-plane queue and state validation passed.")
    return 0


def command_mark(args: argparse.Namespace) -> int:
    _, queue_file, state_dir = resolve_paths(args)
    task_id = normalize_task_id(args.task_id)
    entries = load_queue(queue_file)
    entry = next((item for item in entries if item.id == task_id), None)
    branch = args.branch or (entry.branch if entry else f"codex/{task_id.lower()}")

    state = StateStore(state_dir).mark_task(
        task_id,
        status=args.status,
        branch=branch,
        pr_number=args.pr_number,
        last_error=args.error,
    )

    if args.json:
        print_json(state)
    else:
        print(f"Marked {state['task_id']} as {state['status']}.")
        print(f"State file: {StateStore(state_dir).task_path(task_id)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local agentic development control plane.")
    parser.add_argument("--repo-root", default=".", help="Repository root. Defaults to current directory.")
    parser.add_argument("--queue-file", help="Queue JSON path. Defaults to the existing repo queue.")
    parser.add_argument(
        "--state-dir",
        default=str(DEFAULT_STATE_DIR),
        help="Local ignored runtime state directory.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create the local runtime state directory.")
    init_parser.set_defaults(func=command_init)

    queue_parser = subparsers.add_parser("queue", help="List queue entries.")
    queue_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    queue_parser.add_argument("--status", choices=STATUSES, help="Filter by effective status.")
    queue_parser.set_defaults(func=command_queue)

    status_parser = subparsers.add_parser("status", help="Show local git and task state.")
    status_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    status_parser.set_defaults(func=command_status)

    next_parser = subparsers.add_parser("next", help="Show the next unblocked pending task.")
    next_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    next_parser.set_defaults(func=command_next)

    run_parser = subparsers.add_parser("run", help="Report planned actions for a task.")
    run_parser.add_argument("--task-id", help="Task id to inspect. Defaults to next unblocked task.")
    run_parser.add_argument("--dry-run", action="store_true", help="Required in TOOL-005.")
    run_parser.add_argument("--repo", default=REPO_NAME, help="GitHub repository name for gh inspection.")
    run_parser.set_defaults(func=command_run)

    validate_parser = subparsers.add_parser("validate", help="Validate queue and local state JSON.")
    validate_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    validate_parser.set_defaults(func=command_validate)

    mark_parser = subparsers.add_parser("mark", help="Mark task runtime state locally.")
    mark_parser.add_argument("task_id")
    mark_parser.add_argument("--status", required=True, choices=STATUSES)
    mark_parser.add_argument("--branch")
    mark_parser.add_argument("--pr-number", type=int)
    mark_parser.add_argument("--error")
    mark_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    mark_parser.set_defaults(func=command_mark)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
