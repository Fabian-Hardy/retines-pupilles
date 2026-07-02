# Rétines & Pupilles — Product Roadmap

This roadmap defines the versioned delivery plan for Rétines & Pupilles. Each version must be production-deliverable, even if the product remains incomplete until later versions.

## Delivery principles

- Every version must be deployable to production.
- Every task must be implemented through a dedicated branch and pull request.
- `develop` and `main` must not receive direct commits.
- Codex/agent work must be scoped to one task at a time.
- CI, review, and validation are required before merge.
- Security, privacy, and rollback must be considered before production deployment.

## Current baseline

The repository has completed the initial backend foundation and Patient CRUD path through `TASK-009`.

Completed baseline:

- `TASK-001` — FastAPI skeleton
- `TASK-002` — Persistence foundation
- `TASK-003` — Domain base models
- `TASK-004` — Patient model
- `TASK-005` — Patient schemas
- `TASK-006` — Patient CRUD helpers
- `TASK-007` — Patient API endpoints
- `TASK-008` — Project progress page
- `TASK-009` — Patient update/delete endpoints

---

## v0.2.0 — Backend Patient security baseline

Goal: complete the Patient API contract and introduce the authentication/user foundation.

- `TASK-010` — Patient list filtering and pagination
- `TASK-011` — Authentication foundation with Authlib
- `TASK-013` — User model and migrations
- `TASK-014` — Password and credential handling
- `TASK-015` — Login/logout/me API
- `TASK-016` — Role-based access control
- `TASK-017` — Protect Patient API with auth
- `TASK-018` — Standard API error contract

Production deliverable:

- Patient API supports filtered and paginated listing.
- Users and roles exist.
- Authentication endpoints exist.
- Patient API is protected.
- Backend validation is green.

---

## v0.3.0 — Frontend Patient MVP

Goal: provide a usable web interface for Patient management.

- `TASK-012` — Frontend application shell
- `TASK-019` — Frontend tooling and Docker build
- `TASK-020` — Typed API client
- `TASK-021` — Login/logout frontend
- `TASK-022` — Patient list page
- `TASK-023` — Patient detail page
- `TASK-024` — Patient create form
- `TASK-025` — Patient edit form
- `TASK-026` — Patient archive/delete flow
- `TASK-027` — Frontend smoke tests

Production deliverable:

- Web app shell is deployed.
- Users can log in and manage patients through the UI.
- Frontend build succeeds through Docker.

---

## v0.4.0 — Optical prescriptions

Goal: add the core optical prescription domain.

- `TASK-028` — Optical prescription model
- `TASK-029` — Prescription Alembic migration
- `TASK-030` — Prescription schemas
- `TASK-031` — Prescription CRUD helpers
- `TASK-032` — Prescription API endpoints
- `TASK-033` — Prescription frontend patient tab
- `TASK-034` — Prescription validation rules
- `TASK-035` — Prescription history view

Production deliverable:

- Prescriptions can be created, viewed, updated, and listed per patient.
- Prescription history is available in the patient UI.

---

## v0.5.0 — Quotes and sales orders

Goal: support the commercial customer workflow.

- `TASK-036` — Quote model
- `TASK-037` — Quote line model
- `TASK-038` — Sales order model
- `TASK-039` — Order status lifecycle
- `TASK-040` — Quote/order API endpoints
- `TASK-041` — Quote/order frontend
- `TASK-042` — Convert quote to order
- `TASK-043` — Order printable summary
- `TASK-044` — Order search and filtering

Production deliverable:

- Quotes can be created and converted into orders.
- Orders can be tracked by status.

---

## v0.6.0 — Product catalog, suppliers, and stock

Goal: manage products, suppliers, and basic inventory.

- `TASK-045` — Product catalog model
- `TASK-046` — Product category model
- `TASK-047` — Brand model
- `TASK-048` — Supplier model
- `TASK-049` — Product API endpoints
- `TASK-050` — Product frontend pages
- `TASK-051` — Stock movement model
- `TASK-052` — Stock adjustment API
- `TASK-053` — Low-stock alerts
- `TASK-054` — Supplier order draft

Production deliverable:

- Products and suppliers are manageable.
- Basic stock movements are tracked.

---

## v0.7.0 — Patient documents

Goal: attach and secure patient-related documents.

- `TASK-055` — Document metadata model
- `TASK-056` — Secure file storage strategy
- `TASK-057` — Document upload API
- `TASK-058` — Document download API
- `TASK-059` — Document delete/archive API
- `TASK-060` — Document frontend tab
- `TASK-061` — File type and size validation
- `TASK-062` — Document access audit

Production deliverable:

- Patient documents can be uploaded, accessed, and audited securely.

---

## v0.8.0 — Legacy data import

Goal: import existing data in a controlled and auditable way.

- `TASK-063` — Legacy import architecture
- `TASK-064` — DBF reader
- `TASK-065` — Encoding detection
- `TASK-066` — Legacy patient mapping
- `TASK-067` — Duplicate detection
- `TASK-068` — Import dry-run mode
- `TASK-069` — Import reconciliation report
- `TASK-070` — Import CLI command
- `TASK-071` — Import anonymized fixtures
- `TASK-072` — Import production runbook

Production deliverable:

- Legacy import can be rehearsed, validated, and executed with reports.

---

## v0.9.0 — Security, privacy, and compliance baseline

Goal: prepare a responsible production baseline for sensitive patient data.

- `TASK-073` — Audit log model
- `TASK-074` — Audit middleware/service
- `TASK-075` — Audit admin view
- `TASK-076` — Rate limiting with Redis
- `TASK-077` — CORS and security headers hardening
- `TASK-078` — Session/token hardening
- `TASK-079` — User access review screen
- `TASK-080` — Patient data export
- `TASK-081` — Data rectification workflow
- `TASK-082` — Data archive/anonymization workflow
- `TASK-083` — Privacy notice documentation
- `TASK-084` — Processing register documentation
- `TASK-085` — Backup encryption policy

Production deliverable:

- Access is auditable.
- Rate limits and security headers are hardened.
- Core privacy workflows and documentation exist.

---

## v1.0.0 — Stable production release

Goal: release the first stable production version.

- `TASK-086` — Production deployment checklist
- `TASK-087` — Database migration release process
- `TASK-088` — Automated encrypted backups
- `TASK-089` — Restore drill
- `TASK-090` — Health checks
- `TASK-091` — Structured logging
- `TASK-092` — Monitoring and alerts
- `TASK-093` — Admin documentation
- `TASK-094` — User documentation
- `TASK-095` — End-to-end critical path tests
- `TASK-096` — User acceptance testing
- `TASK-097` — Production launch
- `TASK-098` — Post-launch stabilization

Production deliverable:

- Stable v1.0.0 is deployed.
- Backup/restore, monitoring, documentation, and critical path tests are in place.

---

## v1.1.0 — Field stabilization and reporting

Goal: improve the product after real usage.

- `TASK-099` — Post-launch bugfix batch
- `TASK-100` — UX improvements from real use
- `TASK-101` — Faster patient search
- `TASK-102` — Better order filters
- `TASK-103` — Export patient summary PDF
- `TASK-104` — Export order summary PDF
- `TASK-105` — Admin dashboard v1

Production deliverable:

- First field feedback is integrated.
- Basic reporting and PDF exports are available.

---

## v1.2.0 — Payment tracking and accounting exports

Goal: track customer payment status and provide accounting exports.

- `TASK-106` — Payment tracking model
- `TASK-107` — Deposit and balance fields
- `TASK-108` — Payment status workflow
- `TASK-109` — Payment frontend
- `TASK-110` — Daily sales export
- `TASK-111` — Accounting export v1

Production deliverable:

- Payment status, deposit, and balance can be tracked.
- Accounting exports are available.

---

## v1.3.0 — Customer communication

Goal: add controlled customer notifications.

- `TASK-112` — Email notification foundation
- `TASK-113` — Order ready notification
- `TASK-114` — Appointment reminder notification
- `TASK-115` — Notification templates
- `TASK-116` — Notification opt-in/opt-out
- `TASK-117` — Notification audit log

Production deliverable:

- Customer notifications are available with audit and opt-out support.

---

## v1.4.0 — Advanced appointments

Goal: make appointment management operationally useful.

- `TASK-118` — Appointment calendar view
- `TASK-119` — Appointment status workflow
- `TASK-120` — Staff availability model
- `TASK-121` — Appointment conflict detection
- `TASK-122` — Appointment reminders
- `TASK-123` — Appointment analytics

Production deliverable:

- Appointment calendar and reminders are operational.

---

## v1.5.0 — Advanced inventory

Goal: improve stock reliability and supplier workflows.

- `TASK-124` — Inventory valuation fields
- `TASK-125` — Supplier order workflow
- `TASK-126` — Reception of supplier orders
- `TASK-127` — Stock discrepancy reports
- `TASK-128` — Product barcode/reference search
- `TASK-129` — Stock export

Production deliverable:

- Stock discrepancies and supplier receptions are trackable.

---

## v1.6.0 — Business reporting

Goal: provide operational dashboards and exports.

- `TASK-130` — Sales dashboard
- `TASK-131` — Patient activity dashboard
- `TASK-132` — Product performance report
- `TASK-133` — Prescription activity report
- `TASK-134` — Exportable CSV reports
- `TASK-135` — Date-range analytics

Production deliverable:

- Business reporting is available for daily management.

---

## v1.7.0 — Long-term maintenance baseline

Goal: make maintenance safer and more predictable.

- `TASK-136` — Test coverage thresholds
- `TASK-137` — Regression test suite
- `TASK-138` — Dependency update workflow
- `TASK-139` — Security scan automation
- `TASK-140` — Backup retention automation
- `TASK-141` — Database maintenance tasks

Production deliverable:

- Maintenance and updates are more automated and safer.

---

## v2.0.0 — Multi-store architecture

Goal: support multiple stores or organizations. This is a likely major version because it changes data scoping assumptions.

- `TASK-142` — Organization/store model
- `TASK-143` — Store-scoped patients
- `TASK-144` — Store-scoped users and roles
- `TASK-145` — Store-scoped stock
- `TASK-146` — Store-scoped orders
- `TASK-147` — Cross-store admin role
- `TASK-148` — Data migration to store scope

Production deliverable:

- The application supports store-scoped data and roles.

---

## v2.1.0 — External integrations

Goal: introduce controlled external integrations.

- `TASK-149` — Supplier integration architecture
- `TASK-150` — Accounting software connector
- `TASK-151` — Calendar external sync
- `TASK-152` — Import/export API keys
- `TASK-153` — Integration audit log
- `TASK-154` — Integration failure dashboard

Production deliverable:

- External connectors are available with audit and failure visibility.

---

## v2.2.0 — PWA and tablet usage

Goal: improve mobile and tablet usage.

- `TASK-155` — Responsive tablet layout
- `TASK-156` — PWA manifest
- `TASK-157` — Offline-safe read-only cache
- `TASK-158` — Touch-friendly patient forms
- `TASK-159` — Camera document capture
- `TASK-160` — Mobile smoke tests

Production deliverable:

- The application is practical on tablets and mobile browsers.

---

## v2.3.0 — Operational automation

Goal: automate internal follow-up work.

- `TASK-161` — Task/reminder model
- `TASK-162` — Internal task assignment
- `TASK-163` — Follow-up reminders
- `TASK-164` — Order delay alerts
- `TASK-165` — Patient follow-up workflows
- `TASK-166` — Staff notification center

Production deliverable:

- Staff can manage reminders and follow-up tasks in the application.

---

## v3.0.0 — Assisted document intelligence

Goal: add OCR/document intelligence with explicit human validation.

- `TASK-167` — OCR pipeline architecture
- `TASK-168` — Prescription document OCR
- `TASK-169` — Human validation queue
- `TASK-170` — OCR confidence scoring
- `TASK-171` — OCR audit trail
- `TASK-172` — OCR privacy/security review

Production deliverable:

- OCR can assist document processing, but human validation remains mandatory.
