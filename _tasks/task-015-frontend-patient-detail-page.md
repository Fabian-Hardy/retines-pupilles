TASK-015 - Frontend patient detail page

Repository: Fabian-Hardy/retines-pupilles
Base branch: develop
Expected branch: feature/task-015-frontend-patient-detail-page
Target version: v0.2.0

Context:
- The frontend shell is in frontend/src and uses Vite, React, and TypeScript.
- Patient list and patient mutation work may exist from earlier Sprint 1 tasks.
- The backend already exposes GET /api/v1/patients/{patient_id}.
- Follow AGENTS.md.

Objective:
Add a patient detail page, connect the patient list to that page, display available patient information, and handle loading, not-found, and error states.

Requirements:
1. Add a route/view for patient detail using the existing patient ID path pattern chosen by the frontend router.
2. Link patient list rows or actions to the corresponding detail page.
3. Fetch patient details from GET /api/v1/patients/{patient_id}.
4. Display the patient fields returned by the API in a readable layout.
5. Handle loading, 404/not found, and generic error states.
6. Reuse patient API helpers and presentation conventions from TASK-014 where practical.
7. Respect the protected routing/session model from TASK-013.

Acceptance criteria:
- Navigation from the patient list to a patient detail page works.
- The detail page renders available patient information clearly.
- Loading, not-found, and generic error states are handled without blank screens.
- No absent medical data is invented in the UI.
- Frontend validation passes.
- CI is green.

Validation commands:
- Set-Location frontend; npm run typecheck

Dependencies and sequencing:
- Depends on TASK-013 for protected routing and session handling.
- Runs after TASK-014 to reduce conflicts in patient API helpers, labels, and navigation patterns.
- Do not modify backend behavior unless a strictly necessary bug fix is identified and documented in the PR.

Constraints:
- Do not invent medical or prescription fields that are absent from the backend schema.
- Do not introduce broad routing rewrites unrelated to patient detail navigation.
- Do not log patient-sensitive data.
- Do not weaken existing tests or validation.
