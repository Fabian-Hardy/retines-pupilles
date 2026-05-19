# TASKS.md — Rétines & Pupilles

> Fichier géré par Cowork (superviseur). Lu par Claude Code avant chaque session.
> Format : une tâche = contexte précis + critères d'acceptance mesurables.
> Ne pas modifier les critères d'acceptance sans accord de Fabian.

## Statuts

- 🔴 TODO — pas encore démarré
- 🟡 IN PROGRESS — en cours (indiquer qui travaille dessus)
- 🟢 DONE — terminé, PR créée
- 🔵 REVIEW — PR en attente de review Fabian

---

## Sprint 1 — Fondations

### TASK-001 — Structure backend FastAPI 🔴

**Contexte :** Créer le squelette du backend Python avec FastAPI. Point de départ de toute la stack.
Le backend tourne dans Docker (voir `docker-compose.yml`). La config vient exclusivement de `.env` via Pydantic Settings.

**Fichiers à créer :**
- `backend/app/main.py` — app FastAPI, CORS configuré pour `APP_DOMAIN`, middleware logging
- `backend/app/core/config.py` — classe `Settings` Pydantic BaseSettings, lecture depuis `.env`
- `backend/app/core/database.py` — moteur SQLAlchemy async, `get_db` dependency
- `backend/app/api/v1/router.py` — router principal qui inclut tous les endpoints
- `backend/app/api/v1/endpoints/health.py` — `GET /api/v1/health` → `{"status": "ok", "version": "x.y.z"}`
- `backend/Dockerfile` — multi-stage : `builder` (pip install) + `runtime` (image slim, user non-root)
- `backend/pyproject.toml` — dépendances : `fastapi[standard]`, `sqlalchemy[asyncio]`, `alembic`, `pydantic-settings`, `asyncpg`, `redis[hiredis]`, `python-jose[cryptography]`, `passlib[bcrypt]`, `dbfread`, `chardet`, `rapidfuzz`

**Critères d'acceptance :**
- [ ] `docker compose -f docker-compose.yml -f docker-compose.dev.yml up backend` démarre sans erreur
- [ ] `curl localhost:8000/api/v1/health` retourne `{"status":"ok","version":"0.1.0"}`
- [ ] `mypy backend/` passe sans erreur (strict mode)
- [ ] `ruff check backend/` passe sans erreur
- [ ] L'image Docker `retines-backend` fait moins de 200 MB

---

### TASK-002 — Structure frontend React 🔴

**Contexte :** Créer le squelette du frontend React avec Vite, TypeScript strict et TailwindCSS.
Le frontend sert de SPA. En prod, servi par nginx dans le conteneur Docker. En dev, hot reload Vite sur port 5173.

**Fichiers à créer :**
- `frontend/` — scaffold Vite + React 18 + TypeScript strict
- `frontend/src/App.tsx` — composant racine, routing React Router v6
- `frontend/src/main.tsx` — point d'entrée, StrictMode
- `frontend/tailwind.config.ts` — config TailwindCSS avec palette couleurs du projet
- `frontend/tsconfig.json` — strict: true, paths configurés
- `frontend/vite.config.ts` — proxy `/api` → `http://backend:8000` en dev
- `frontend/Dockerfile` — multi-stage : `development` (node + vite dev) + `builder` (vite build) + `runtime` (nginx:alpine, fichiers static)
- `frontend/nginx.conf` — nginx config pour SPA (try_files vers index.html)
- `frontend/package.json` — deps : react, react-dom, react-router-dom, @tanstack/react-query, axios, @openapi-ts (génération client), lucide-react

**Critères d'acceptance :**
- [ ] `docker compose -f docker-compose.yml -f docker-compose.dev.yml up frontend` démarre sans erreur
- [ ] Page d'accueil visible sur `http://localhost:5173`
- [ ] `tsc --noEmit` passe sans erreur
- [ ] `npm run build` produit un bundle fonctionnel dans `dist/`
- [ ] L'image Docker `retines-frontend` (runtime) fait moins de 50 MB

---

### TASK-003 — Modèles DB + migrations Alembic 🔴

**Contexte :** Définir le modèle de données complet. Se référer à `docs/architecture/data-merge.md` pour
la logique de fusion entre la base principale et la base Allyson. Les champs `source`, `external_id`,
`allyson_modified_fields` et `last_import_hash` sont critiques pour le mécanisme d'import.

**Fichiers à créer :**
- `backend/app/models/__init__.py`
- `backend/app/models/client.py` — modèle `Client`
- `backend/app/models/prescription.py` — modèle `Prescription`
- `backend/app/models/commande.py` — modèle `Commande` + `LigneCommande`
- `backend/app/models/article.py` — modèle `Article` (stock)
- `backend/app/models/facture.py` — modèle `Facture`
- `backend/alembic/` — configuration Alembic avec `env.py` async
- `backend/alembic/versions/001_initial.py` — première migration créant toutes les tables

**Champs obligatoires sur `Client` (validé par Allyson, mai 2026) :**
```python
# Champs métier REQUIRED (réponses questionnaire Allyson)
nom: str              # REQUIRED — indispensable
prenom: str           # REQUIRED — indispensable
date_naissance: date  # REQUIRED — indispensable (identifiant métier clé)
gsm: str | None       # REQUIRED — principal moyen de contact
# Champs optionnels (pas indispensables selon Allyson)
adresse: str | None        # optionnel — vient éventuellement de l'import EDOPT
email: str | None          # optionnel
telephone_fixe: str | None # optionnel
mutuelle: str | None       # optionnel
notes: str | None          # optionnel
preference_contact: str | None  # optionnel — "sms"|"email"|"tel"|"tous"
# Champs techniques merge
source: str              # "main_db" | "allyson" — origine de la fiche
external_id: str         # ID dans la base source (pour dédupliq)
allyson_modified_fields: list[str]  # JSON array — champs modifiés par Allyson
last_import_hash: str    # SHA256 de la dernière version importée
```

**Note doublons :** Allyson préfère garder deux fiches séparées. L'interface signale les doublons potentiels (même nom + date naissance) mais ne fusionne jamais sans action explicite.

**Critères d'acceptance :**
- [ ] `alembic upgrade head` depuis le conteneur backend crée toutes les tables sans erreur
- [ ] `alembic downgrade -1` fonctionne (rollback propre)
- [ ] `alembic downgrade base` puis `alembic upgrade head` = idempotent
- [ ] Toutes les FK sont cohérentes (pas de FK cassée)
- [ ] Indexes sur : `client.external_id`, `client.source`, `commande.client_id`, `facture.commande_id`

---

### TASK-004 — Authentification JWT 🔴

**Contexte :** Auth simple JWT (access token 15 min + refresh token 7 jours).
Seuls Fabian et Allyson utilisent l'app — pas d'inscription publique. Création de comptes par CLI/admin uniquement.

**Fichiers à créer :**
- `backend/app/api/v1/endpoints/auth.py` — `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh`, `POST /api/v1/auth/logout`
- `backend/app/core/security.py` — helpers JWT (create_token, verify_token), hashing bcrypt
- `backend/app/models/user.py` — modèle `User` (id, email, hashed_password, is_active, role)
- `backend/app/schemas/auth.py` — Pydantic schemas LoginRequest, TokenResponse
- `backend/app/api/deps.py` — dependency `get_current_user`

**Critères d'acceptance :**
- [ ] `POST /api/v1/auth/login` avec bonnes credentials → retourne access_token + refresh_token
- [ ] `POST /api/v1/auth/login` avec mauvaises credentials → 401
- [ ] Un endpoint protégé renvoie 401 sans token valide
- [ ] Refresh token révocable (stocké dans Redis, supprimé au logout)

---

### TASK-005 — Import base DBF (Allyson) 🔴

**Contexte :** La base de données actuelle d'Allyson est au format DBF (logiciel legacy).
Le module d'import doit lire les fichiers DBF, les normalis