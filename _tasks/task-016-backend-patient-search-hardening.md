TASK-016 - Backend patient search hardening

Repository: Fabian-Hardy/retines-pupilles
Base branch: develop
Expected branch: feature/task-016-backend-patient-search-hardening
Target version: v0.2.0

Context:
- Patient API code is in backend/app/api/v1/endpoints/patients.py.
- Patient CRUD helpers are in backend/app/crud/patient.py.
- Patient schemas are in backend/app/schemas/patient.py.
- Existing patient tests are in backend/tests/test_patient_api.py and backend/tests/test_patient_crud.py.
- Follow AGENTS.md.

Objective:
Harden patient search, filtering, and pagination behavior with focused backend tests, and improve API errors only if the tests expose a necessary correction.

Requirements:
1. Add or expand backend tests for GET /api/v1/patients search, filters, total count, and pagination.
2. Cover empty filters and whitespace-only values according to the current intended API behavior.
3. Cover invalid query values, including invalid pagination limits and invalid typed filters such as country_code or preferred_language.
4. Cover pagination boundaries and verify total represents matching rows before pagination.
5. Cover combined filters where useful to document expected behavior.
6. Keep behavior changes minimal and compatible; update API or CRUD code only if required to satisfy a clearly documented test expectation.
7. Preserve existing patient create, read, update, delete, and list behavior.

Acceptance criteria:
- Backend tests document search, filtering, and pagination edge cases.
- Invalid inputs produce consistent FastAPI validation or documented API errors.
- No incompatible API change is introduced without explicit PR justification.
- Ruff passes.
- Mypy passes.
- Pytest passes.
- CI is green.

Validation commands:
- Set-Location backend; ruff check app/
- Set-Location backend; mypy app/
- Set-Location backend; pytest tests/ -v

Dependencies and sequencing:
- Depends on TOOL-004 seeding this queue.
- Runs after TASK-013, TASK-014, and TASK-015 in the Sprint 1 queue to avoid changing patient API behavior underneath in-progress frontend work.
- If a frontend-visible API behavior change becomes necessary, document it in the PR and call out any follow-up frontend work.

Constraints:
- Do not create destructive migrations.
- Do not introduce incompatible API behavior without justification.
- Do not modify authentication unless strictly necessary for test setup.
- Do not log patient-sensitive data.
- Do not weaken or remove tests to make CI pass.
