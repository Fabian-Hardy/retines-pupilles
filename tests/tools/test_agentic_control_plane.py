from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.agentic_control_plane import (
    QueueEntry,
    StateStore,
    evaluate_merge_policy,
    find_next_task,
    load_queue,
    main,
)


class AgenticControlPlaneTest(unittest.TestCase):
    def test_load_queue_normalizes_existing_legacy_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            queue_path = Path(tmp) / "queue.json"
            queue_path.write_text(
                json.dumps(
                    [
                        {
                            "id": "TASK-014",
                            "title": "Password and credential handling",
                            "risk": "medium",
                            "branch": "codex/task-014-password-credential-handling",
                            "dependencies": ["TASK-013"],
                            "allow_auto_merge": "false",
                            "validation": "backend",
                            "files": ["backend/app/core/security.py", "backend/tests/"],
                        }
                    ]
                ),
                encoding="utf-8",
            )

            entries = load_queue(queue_path)

        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry.id, "TASK-014")
        self.assertEqual(entry.status, "pending")
        self.assertEqual(entry.depends_on, ("TASK-013",))
        self.assertEqual(entry.risk_level, "medium")
        self.assertFalse(entry.allow_auto_merge)
        self.assertIn("cd backend", entry.validation_commands[0])

    def test_state_store_marks_task_with_required_runtime_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = StateStore(Path(tmp) / ".local/agentic-control-plane")

            state = store.mark_task(
                "TOOL-005",
                status="pr_open",
                branch="tool/tool-005-local-agentic-control-plane",
                pr_number=42,
            )
            loaded = store.load_task("TOOL-005")

        self.assertEqual(state["task_id"], "TOOL-005")
        self.assertEqual(loaded["status"], "pr_open")
        self.assertEqual(loaded["pr_number"], 42)
        self.assertIn("timestamps", loaded)
        self.assertIn("validation_results", loaded)
        self.assertIn("codex", loaded["log_paths"])
        self.assertIn("run_json", loaded["log_paths"])

    def test_find_next_task_requires_dependencies_to_be_merged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = StateStore(Path(tmp) / "state")
            store.mark_task("TASK-001", status="merged", branch="codex/task-001")
            entries = [
                QueueEntry(
                    id="TASK-001",
                    title="Done",
                    branch="codex/task-001",
                    status="pending",
                    depends_on=(),
                    risk_level="low",
                    allow_auto_merge=False,
                    validation_commands=(),
                    notes=(),
                ),
                QueueEntry(
                    id="TASK-002",
                    title="Ready",
                    branch="codex/task-002",
                    status="pending",
                    depends_on=("TASK-001",),
                    risk_level="low",
                    allow_auto_merge=False,
                    validation_commands=(),
                    notes=(),
                ),
                QueueEntry(
                    id="TASK-003",
                    title="Blocked",
                    branch="codex/task-003",
                    status="pending",
                    depends_on=("TASK-099",),
                    risk_level="low",
                    allow_auto_merge=False,
                    validation_commands=(),
                    notes=(),
                ),
            ]

            next_task = find_next_task(entries, store)

        self.assertIsNotNone(next_task)
        self.assertEqual(next_task.id, "TASK-002")

    def test_merge_policy_reports_ready_only_for_low_risk_safe_signals(self) -> None:
        entry = QueueEntry(
            id="TOOL-005",
            title="Control plane",
            branch="tool/tool-005-local-agentic-control-plane",
            status="pending",
            depends_on=(),
            risk_level="low",
            allow_auto_merge=True,
            validation_commands=("python -m unittest tests.tools.test_agentic_control_plane",),
            notes=(),
            files=("tools/agentic_control_plane.py", "tests/tools/"),
        )

        decision = evaluate_merge_policy(
            entry,
            pr_is_draft=False,
            ci_green=True,
            changed_files=("tools/agentic_control_plane.py", "tests/tools/test_agentic_control_plane.py"),
        )

        self.assertTrue(decision.mergeable)
        self.assertEqual(decision.status, "ready_to_merge")

    def test_merge_policy_blocks_drafts_secrets_and_medium_risk(self) -> None:
        entry = QueueEntry(
            id="TASK-020",
            title="Typed API client",
            branch="codex/task-020-typed-api-client",
            status="pending",
            depends_on=(),
            risk_level="medium",
            allow_auto_merge=True,
            validation_commands=(),
            notes=(),
            files=("frontend/src/",),
        )

        decision = evaluate_merge_policy(
            entry,
            pr_is_draft=True,
            ci_green=True,
            changed_files=("frontend/src/api.ts",),
            diff_text='+const token = "super-secret-value";',
        )

        failed_checks = {check.name for check in decision.checks if not check.passed}
        self.assertFalse(decision.mergeable)
        self.assertEqual(decision.status, "needs_human")
        self.assertIn("pr_not_draft", failed_checks)
        self.assertIn("no_secrets_detected", failed_checks)
        self.assertIn("risk_level_low", failed_checks)

    def test_run_without_dry_run_refuses_before_side_effects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            queue_path = repo_root / "queue.json"
            queue_path.write_text(
                json.dumps(
                    [
                        {
                            "id": "TOOL-005",
                            "title": "Control plane",
                            "branch": "tool/tool-005-local-agentic-control-plane",
                            "risk_level": "low",
                            "allow_auto_merge": False,
                        }
                    ]
                ),
                encoding="utf-8",
            )

            exit_code = main(
                [
                    "--repo-root",
                    str(repo_root),
                    "--queue-file",
                    str(queue_path),
                    "run",
                    "--task-id",
                    "TOOL-005",
                ]
            )

        self.assertEqual(exit_code, 2)


if __name__ == "__main__":
    unittest.main()
