# Workflow Git & déploiement

## Principe général

```
Claude Code / agents dev
        │
        │ travaille sur feature branches
        ▼
   GitHub (repo)
        │
        │ PR créée automatiquement
        ▼
   Fabian review + validation
        │
        │ merge vers main
        ▼
   GitHub Actions CI/CD
        │
        │ SSH → serveur prod
        ▼
   Déploiement automatique
```

**Règle fondamentale :** rien n'arrive en production sans que Fabian l'ait validé explicitement. Claude Code pousse, Fabian approuve, GitHub Actions déploie.

---

## Branches

| Branche | Rôle | Qui pousse | Protection |
|---|---|---|---|
| `main` | Production | GitHub Actions uniquement | ✅ Protégée — push direct interdit |
| `develop` | Intégration | Claude Code + Fabian | 🔒 PR obligatoire |
| `feature/xxx` | Fonctionnalité | Claude Code | Libre |
| `fix/xxx` | Correction de bug | Claude Code | Libre |
| `hotfix/xxx` | Fix urgent prod | Fabian uniquement | Direct sur main via PR |

---

## Flux complet d'une fonctionnalité

### 1. Claude Code crée une branche

```bash
git checkout develop
git pull origin develop
git checkout -b feature/import-dbf-clients
```

### 2. Développement + tests

Claude Code développe la fonctionnalité, écrit les tests, s'assure que tout passe :

```bash
# Tests unitaires
docker compose exec backend pytest tests/unit/

# Tests d'intégration
docker compose exec backend pytest tests/integration/

# Lint et type checking
docker compose exec backend ruff check app/
docker compose exec backend mypy app/

# Frontend
docker compose exec frontend npm run lint
docker compose exec frontend npm run type-check
```

Les **pre-commit hooks** bloquent le commit si les vérifications échouent.

### 3. Commit avec message conventionnel

Format obligatoire : `type(scope): description`

| Type | Usage |
|---|---|
| `feat` | Nouvelle fonctionnalité |
| `fix` | Correction de bug |
| `refactor` | Refactoring sans changement de comportement |
| `test` | Ajout/modification de tests |
| `docs` | Documentation uniquement |
| `chore` | Maintenance (dépendances, config) |
| `perf` | Amélioration de performance |

Exemples :
```bash
git commit -m "feat(import): ajout lecture fichiers DBF avec normalisation dates"
git commit -m "fix(auth): correction expiration token refresh"
git commit -m "test(merge): tests unitaires logique fusion enregistrements"
```

### 4. Push et création PR

```bash
git push origin feature/import-dbf-clients
# GitHub Actions lance automatiquement les tests CI
# GitHub crée automatiquement un lien vers la PR
```

La PR est créée vers `develop`. Le template de PR demande :
- Description de ce qui a été fait
- Comment tester
- Screenshots si UI
- Checklist (tests passent, lint OK, doc mise à jour)

### 5. Fabian review

Fabian reçoit une notification GitHub. Il:
- Lit le diff
- Vérifie que les tests passent (badge CI visible sur la PR)
- Approuve ou demande des modifications
- Merge vers `develop` quand satisfait

### 6. Deploy develop → main (release)

Quand `develop` est stable et prêt pour la production :

```bash
# Fabian crée une PR develop → main
# Après review finale, merge
# GitHub Actions déclenche le déploiement prod automatiquement
```

---

## GitHub Actions — CI

**Fichier :** `.github/workflows/ci.yml`

Déclenché sur : toute PR et tout push sur `develop` ou `main`

```yaml
jobs:
  backend:
    - ruff check (lint Python)
    - mypy (vérification types)
    - pytest (tests unitaires + intégration)
    - coverage > 80% obligatoire sur la logique de fusion DBF

  frontend:
    - eslint
    - tsc --noEmit (vérification types TypeScript)
    - vitest (tests unitaires composants)

  build:
    - docker build backend (vérifie que l'image compile)
    - docker build frontend
```

Un PR ne peut pas être mergé si le CI échoue.

---

## GitHub Actions — Deploy prod

**Fichier :** `.github/workflows/deploy.yml`

Déclenché sur : push sur `main` uniquement

```yaml
jobs:
  deploy:
    - SSH sur 204.168.202.176
    - cd /srv/retines-pupilles
    - git pull origin main
    - docker compose pull
    - docker compose up -d --no-deps --build
    - docker compose exec backend alembic upgrade head  # migrations DB auto
    - health check : curl https://app.[DOMAIN]/api/v1/health
```

**Zero downtime :** Docker Compose redémarre les containers un par un. Traefik maintient les connexions HTTP en cours pendant le redémarrage.

### Secrets GitHub à configurer

Dans GitHub → Settings → Secrets → Actions :

| Secret | Description |
|---|---|
| `PROD_SSH_HOST` | `204.168.202.176` |
| `PROD_SSH_USER` | `root` |
| `PROD_SSH_KEY` | Clé privée SSH pour le serveur (contenu de `mind_hetzner`) |

> Quand l'app migre sur le nouveau serveur d'Allyson, il suffit de mettre à jour ces 3 secrets. Le workflow de déploiement est identique.

---

## Configuration pre-commit

**Fichier :** `.pre-commit-config.yaml` (à la racine du repo)

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    hooks:
      - id: ruff
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    hooks:
      - id: mypy

  - repo: https://github.com/pre-commit/pre-commit-hooks
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files  # bloque les fichiers > 500KB
      - id: no-commit-to-branch      # bloque push direct sur main/develop
        args: ['--branch', 'main', '--branch', 'develop']
```

Installation sur la VM dev :
```bash
pip install pre-commit
pre-commit install
```

---

## Workflow Claude Code

Claude Code travaille depuis la VM dev. Le flux type d'une session :

```
1. Fabian décrit la tâche dans Cowork ou directement dans la VM
2. Claude Code lit CLAUDE.md pour le contexte projet
3. Claude Code crée la branche feature/xxx
4. Claude Code développe, teste, commit
5. Claude Code pousse et notifie Fabian via Cowork : "PR prête : [lien]"
6. Fabian review sur GitHub et merge
7. Deploy automatique si merge sur main
```

**Claude Code ne merge jamais lui-même vers `main` ou `develop`.**

---

## Gestion des versions

Format de version : `MAJOR.MINOR.PATCH` (SemVer)

- `PATCH` : bug fix, pas de nouveau comportement
- `MINOR` : nouvelle fonctionnalité rétrocompatible
- `MAJOR` : changement cassant (rare)

La version est dans `pyproject.toml` (backend) et `package.json` (frontend). Les deux doivent rester synchronisés.

Un tag Git est créé à chaque release :
```bash
git tag -a v1.2.0 -m "Release 1.2.0 — module commandes"
git push origin v1.2.0
```
