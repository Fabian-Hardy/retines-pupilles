TASK-014 - Frontend patient create/edit

Repository: Fabian-Hardy/retines-pupilles
Base branch: develop
Expected branch: feature/task-014-frontend-patient-create-edit
Target version: v0.2.0

Context:
- The frontend shell is in frontend/src and uses Vite, React, and TypeScript.
- Patient create, read, update, delete, and list endpoints already exist under /api/v1/patients.
- Patient API schemas include first_name, last_name, date_of_birth, preferred_language, email, phone, street_line1, street_line2, postal_code, city, and country_code.
- Follow AGENTS.md.

Objective:
Add patient creation and editing UI backed by the existing patient API endpoints, with loading, error, and success states that follow the existing frontend conventions.

Requirements:
1. Add a patient creation flow using the existing POST /api/v1/patients endpoint.
2. Add a patient editing flow using the existing GET /api/v1/patients/{patient_id} and PATCH /api/v1/patients/{patient_id} endpoints.
3. Use typed frontend API contracts that match the backend patient schemas.
4. Capture required fields and available optional fields without inventing medical data that is not in the backend schema.
5. Show clear loading, validation, submission, success, and error states.
6. Preserve any existing patient list behavior and navigation.
7. Reuse the route/session pattern established by TASK-013.

Acceptance criteria:
- A user can create a patient from the UI.
- A user can edit an existing patient from the UI.
- Backend validation errors and network errors are shown clearly.
- Successful create and edit actions give visible feedback and leave the UI in a coherent state.
- The existing patient list is not broken.
- Frontend validation passes.
- CI is green.

Validation commands:
- Set-Location frontend; npm run typecheck

Dependencies and sequencing:
- Depends on TASK-013 for protected routing and session handling.
- Should run before TASK-015 so the detail page can reuse any patient API helpers, field labels, and navigation patterns introduced here.
- If a backend API change appears necessary, document the scope change in the PR before modifying backend code.

Constraints:
- Do not modify the patient database model unless strictly required and justified in the PR.
- Do not add heavy form or state-management dependencies unless the implementation cannot reasonably stay typed and maintainable without them.
- Do not log patient-sensitive data.
- Do not weaken existing tests or validation.
