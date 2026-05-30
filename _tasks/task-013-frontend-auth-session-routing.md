TASK-013 - Frontend auth session routing

Repository: Fabian-Hardy/retines-pupilles
Base branch: develop
Expected branch: feature/task-013-frontend-auth-session-routing
Target version: v0.2.0

Context:
- The frontend is a Vite, React, and TypeScript shell in frontend/src.
- The backend already exposes auth endpoints under /api/v1/auth, including login and current-user reads.
- Vite dev proxy routes /api to the backend service.
- Follow AGENTS.md.

Objective:
Connect the frontend shell to the existing authentication/session state, protect private routes, preserve public routes, and show a minimal user state when a session is present.

Requirements:
1. Reuse the existing backend auth contract. Do not create a parallel auth system.
2. Add typed frontend API/session handling for the existing auth responses.
3. Protect private application routes and handle unauthenticated access cleanly.
4. Keep public routes accessible without a session.
5. Display minimal current-user information in the shell when a valid session is present, such as email or full name.
6. Add logout only if the existing frontend/backend token flow can support it without inventing a separate mechanism.
7. Preserve the current navigation behavior and shell layout unless a scoped routing change is required.

Acceptance criteria:
- Private routes are not reachable in an unauthenticated state.
- Public routes remain reachable without authentication.
- A present valid session displays a minimal current-user state in the shell.
- Unauthenticated and failed-session states are handled without blank screens.
- No credentials, tokens, or secrets are hardcoded or logged.
- Frontend validation passes.
- CI is green.

Validation commands:
- Set-Location frontend; npm run typecheck

Dependencies and sequencing:
- Depends on TOOL-004 seeding this queue.
- This task must run before TASK-014 and TASK-015 so later frontend screens can reuse the same route and session model.
- If implementation requires auth scope beyond the existing backend contract, document the proposed scope change in the PR before expanding it.

Constraints:
- Do not create a parallel auth implementation.
- Do not hardcode credentials.
- Do not store generated secrets in the repository.
- Do not introduce broad CORS changes or authentication bypasses.
- Do not add dependencies unless the routing/session implementation clearly requires them.
