# Rétines & Pupilles — Contexte projet pour Claude Code

> Ce fichier est lu automatiquement par Claude Code à chaque session. Il contient tout ce qu'il faut savoir pour travailler sur ce projet sans réexpliquer le contexte.

## Qu'est-ce que ce projet ?

Logiciel de gestion métier (mini ERP/CRM) pour **Allyson**, opticienne-optométriste à ED Optique Heusy (Belgique). Outil **personnel et autonome** — fonctionne en parallèle du système du magasin, pas en remplacement.

Fabian Hardy est le responsable technique. Il valide toutes les PR avant merge. Claude Code développe, Fabian valide, GitHub Actions déploie.

**Documentation complète : `/docs/`**

## Stack

| Composant | Technologie |
|---|---|
| Backend | Python 3.12 + FastAPI + Pydantic v2 |
| ORM | SQLAlchemy 2.0 async + Alembic (migrations) |
| Frontend | React 19 + TypeScript strict + Vite + TailwindCSS |
| État frontend | Zustand |
| Base de données | PostgreSQL 16 |
| Cache/Sessions | Redis 7 |
| Reverse proxy | Traefik v3 |
| Containerisation | Docker + Docker Compose |
| IA locale | Ollama (llama3.2:3b) — non activé MVP |

## Structure du repo

```
/
├── backend/
│   ├── app/
│   │   ├── api/v1/        ← routes FastAPI
│   │   ├── core/          ← config, sécurité, JWT, middleware
│   │   ├── db/
│   │   │   ├── models/    ← modèles SQLAlchemy
│   │   │   └── migrations/ ← fichiers Alembic (NE PAS ÉDITER MANUELLEMENT)
│   │   ├── schemas/       ← Pydantic schemas I/O
│   │   └── services/      ← logique métier
│   └── tests/
├── frontend/
│   └── src/
│       ├── api/           ← client TypeScript généré (NE PAS ÉDITER MANUELLEMENT)
│       ├── components/
│       ├── pages/
│       └── stores/
├── docs/                  ← documentation complète
├── docker-compose.yml
├── docker-compose.dev.yml
└── CLAUDE.md              ← ce fichier
```

## Règles absolues

### Base de données
- **Jamais modifier le schéma à la main** — toujours via Alembic :
  ```bash
  docker compose exec backend alembic revision --autogenerate -m "description"
  docker compose exec backend alembic upgrade head
  ```
- Les migrations sont versionnées dans Git, ne jamais les modifier après commit

### Client API frontend
- **Jamais éditer `/frontend/src/api/` manuellement** — généré depuis OpenAPI :
  ```bash
  docker compose exec frontend npm run generate:api
  ```
- Après chaque changement d'endpoint backend, régénérer le client

### Logique de fusion DBF — règle critique
Le merge des données importées respecte strictement ces 4 cas (voir `/docs/architecture/data-merge.md`) :
1. Absent → ajouter
2. `source="allyson"` → jamais toucher
3. `source="main_db"`, non modifié par Allyson → écraser
4. `source="main_db"`, modifié par Allyson → fusion champ par champ

**Cette logique doit être couverte à 100% par des tests unitaires.**

### Git
- Jamais push direct sur `main` ou `develop`
- Toujours créer une branche `feature/xxx` ou `fix/xxx`
- Commits en anglais, format conventionnel : `feat(scope): description`
- Créer une PR vers `develop`, notifier Fabian

### Tests
- Tests unitaires obligatoires pour : logique de fusion DBF, validation prescriptions, auth JWT
- Coverage minimum 80% sur `services/`
- Lancer avant chaque commit :
  ```bash
  docker compose exec backend pytest tests/ -v
  docker compose exec backend ruff check app/
  docker compose exec backend mypy app/
  ```

### Secrets
- Jamais de secrets dans le code ou dans Git
- Variables d'env via `.env.dev` (dev) ou `.env.prod` (prod, sur le serveur)
- Voir liste complète : `/docs/dev/env-variables.md`

## Commandes fréquentes

```bash
# Démarrer l'environnement dev
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Tests
docker compose exec backend pytest tests/ -v --cov=app --cov-report=term-missing

# Lint + type check
docker compose exec backend ruff check app/ && docker compose exec backend mypy app/

# Nouvelle migration DB
docker compose exec backend alembic revision --autogenerate -m "ma description"
docker compose exec backend alembic upgrade head

# Régénérer client API frontend
docker compose exec frontend npm run generate:api

# Accéder à la DB
docker compose exec postgresql psql -U retines -d retines_db

# Logs
docker compose logs -f backend
```

## Serveur de production

- **Serveur actuel :** `204.168.202.176` (temporaire — voir `/docs/deploy/migration.md`)
- **Répertoire :** `/srv/retines-pupilles/`
- **Déploiement :** automatique via GitHub Actions sur push `main`
- **Domaine :** `app.[DOMAIN]` (DNS O2switch)

## Points d'attention métier

- **Prescriptions optométriques** : données médicales. Validation stricte des valeurs (sphère, cylindre, axe, addition, écart pupillaire). Ne jamais permettre de valeurs hors plage clinique sans avertissement.
- **Import DBF** : les fichiers EDOPT sont en encodage CP850 (Latin-1). Utiliser `chardet` pour la détection, `dbfread` pour la lecture.
- **Fusion** : voir règle ci-dessus. C'est la fonctionnalité la plus critique de l'app — ne jamais écraser des données saisies par Allyson.
- **Portabilité** : l'app migrera sur un nouveau serveur. Rien ne doit dépendre du serveur hôte. Toute la config passe par `.env`.
