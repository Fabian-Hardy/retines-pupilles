from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.generate_progress_page import (
    build_html,
    extract_task_id,
    normalize_pull_request,
    normalize_roadmap_item,
)


class ProgressPageGeneratorTest(unittest.TestCase):
    def test_extract_task_id_normalizes_task_number(self) -> None:
        self.assertEqual(extract_task_id("feat: add patient API - TASK-007"), "TASK-007")
        self.assertEqual(extract_task_id("feat: add patient API - task 8"), "TASK-008")
        self.assertIsNone(extract_task_id("feat: add patient API"))

    def test_normalize_pull_request_supports_github_api_shape(self) -> None:
        item = normalize_pull_request(
            {
                "number": 8,
                "title": "feat(project): add progress page - TASK-008",
                "merged_at": "2026-05-29T18:00:00Z",
                "html_url": "https://github.com/example/repo/pull/8",
                "user": {"login": "octocat"},
            }
        )

        self.assertEqual(item["number"], 8)
        self.assertEqual(item["task_id"], "TASK-008")
        self.assertEqual(item["author"], "octocat")

    def test_normalize_roadmap_item_validates_task_id(self) -> None:
        item = normalize_roadmap_item(
            {
                "id": "task 9",
                "title": "Patient update/delete endpoints",
                "phase": "Backend",
            }
        )

        self.assertEqual(item["id"], "TASK-009")
        self.assertEqual(item["title"], "Patient update/delete endpoints")

    def test_build_html_shows_done_and_remaining_tasks(self) -> None:
        html = build_html(
            [
                {
                    "number": 8,
                    "title": "feat(project): <progress> - TASK-008",
                    "task_id": "TASK-008",
                    "merged_at": "2026-05-29T18:00:00Z",
                    "html_url": "https://github.com/example/repo/pull/8",
                    "author": "octocat",
                }
            ],
            repo="example/repo",
            base="develop",
            roadmap=[
                {
                    "id": "TASK-008",
                    "title": "Project progress page",
                    "phase": "Project",
                    "description": "Show project status.",
                },
                {
                    "id": "TASK-009",
                    "title": "Patient update/delete endpoints",
                    "phase": "Backend",
                    "description": "Add PATCH and DELETE patient endpoints.",
                },
            ],
            generated_at=datetime(2026, 5, 29, 18, 30, tzinfo=timezone.utc),
        )

        self.assertIn("Retines & Pupilles", html)
        self.assertIn("TASK-008", html)
        self.assertIn("TASK-009", html)
        self.assertIn("Terminee", html)
        self.assertIn("A faire", html)
        self.assertIn("Patient update/delete endpoints", html)
        self.assertIn("&lt;progress&gt;", html)
        self.assertIn("Taches restantes", html)


if __name__ == "__main__":
    unittest.main()
