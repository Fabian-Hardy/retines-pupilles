TASK-010 — Patient list filtering and pagination

Repository: Fabian-Hardy/retines-pupilles
Base branch: develop
Expected branch: chatgpt/task-010-patient-list-filtering-pagination
Target version: v0.2.0

Context:
- This repository uses FastAPI, SQLAlchemy async, Alembic, Pydantic, pytest, ruff, and mypy.
- Existing patient endpoint code is in backend/app/api/v1/endpoints/patients.py.
- Existing patient CRUD helpers are in backend/app/crud/patient.py.
- Existing patient schemas are in backend/app/schemas/patient.py.
- Follow AGENTS.md.

Objective:
Improve GET /api/v1/patients with filters, search, total count, and a structured paginated response.

Requirements:
1. Update GET /api/v1/patients to return:
   {
     "items": list[PatientRead],
     "total": int,
     "offset": int,
     "limit": int
   }

2. Add a PatientListResponse schema.

3. Support optional filters:
   - q
   - first_name
   - last_name
   - email
   - city
   - postal_code
   - country_code
   - preferred_language

4. q must search at least first name, last name, email, and phone.

5. total must represent the number of matching rows before pagination.

6. Keep stable ordering.

7. Validate pagination:
   - offset >= 0
   - limit >= 1
   - limit <= 100

8. Add tests for:
   - default list response shape
   - pagination offset/limit
   - filtering by last_name
   - filtering by city
   - filtering by preferred_language
   - q search
   - invalid pagination values

Validation commands:
- docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm backend ruff check .
- docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm backend mypy app tests --show-traceback
- docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm backend pytest

Constraints:
- Do not modify main or develop directly.
- Keep the PR scoped to TASK-010.
- Do not remove or weaken tests.
- Do not change the Patient database model unless strictly required and justified in the PR.
