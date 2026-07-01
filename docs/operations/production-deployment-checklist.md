# Checklist de déploiement production — Rétines & Pupilles

> TASK-086. Document opérationnel uniquement — aucun comportement applicatif n'est modifié par ce fichier.
> Distingue explicitement **staging** et **production**. Ne contient aucun secret réel : uniquement des noms de variables/secrets, jamais de valeurs.

## 0. Portée

- **Staging** : environnement de validation avant production, mêmes images Docker, mêmes migrations, données de test.
- **Production** : serveur exposé aux utilisateurs réels (Allyson), actuellement `204.168.202.176` (temporaire, voir `docs/deploy/migration.md`).
- Toujours dérouler cette checklist sur staging avant de la dérouler sur production, sauf pour un premier déploiement où il n'existe pas encore de staging séparé (dans ce cas, traiter le premier passage comme un smoke test renforcé).

## 1. Prérequis avant tout déploiement

- [ ] La branche `main` contient exactement ce qui doit partir en prod (merge `develop` → `main` effectué et revu).
- [ ] La CI est verte sur le commit à déployer (voir `.github/workflows/ci.yml` — depuis TASK-091/fix ci, ce badge reflète un résultat réel de ruff/mypy/pytest/tsc/eslint).
- [ ] Le serveur cible a Docker + Docker Compose installés (voir `docs/dev/infra-setup.md`, étapes 1-3).
- [ ] Traefik est déployé et fonctionnel sur le serveur cible (`traefik/setup.sh`).
- [ ] Le DNS pointe vers la bonne IP (`app.retineetpupille.be`, `docs.retineetpupille.be`, `www.retineetpupille.be`).
- [ ] Un dump PostgreSQL récent existe (voir section Sauvegardes).

## 2. Secrets requis

Aucune valeur ci-dessous n'est un secret réel — uniquement les noms attendus. Les valeurs vivent dans `.env.prod` sur le serveur (jamais dans Git) et dans les GitHub Secrets du repo (Settings → Secrets and variables → Actions) :

| Secret | Où il est utilisé |
|---|---|
| `PROD_SERVER_HOST` | Déploiement GitHub Actions |
| `PROD_SERVER_USER` | Déploiement GitHub Actions |
| `PROD_SERVER_SSH_KEY` | Déploiement GitHub Actions |
| `PROD_SERVER_PATH` | Déploiement GitHub Actions (`/srv/retines-pupilles`) |
| `APP_SECRET_KEY` | `.env.prod` sur le serveur |
| `JWT_SECRET_KEY` | `.env.prod` sur le serveur |
| `DB_PASS` / `POSTGRES_PASSWORD` | `.env.prod` sur le serveur |
| `REDIS_PASSWORD` | `.env.prod` sur le serveur, si Redis sécurisé |

Voir `.env.example` à la racine pour la liste complète des variables attendues.

- [ ] Tous les secrets ci-dessus existent et sont à jour (pas de valeur `change_me_*` restante).
- [ ] `.env.prod` n'est jamais commité dans Git (vérifier `.gitignore`).

## 3. Images Docker

- [ ] `docker compose build` (prod) réussit localement ou en CI sans erreur.
- [ ] Image backend : CONTENT SIZE < 150 MB (critère du projet, voir `PROJECT_STATE.md`).
- [ ] Image frontend : < 50 MB (nginx:alpine).
- [ ] Les images sont taguées de façon traçable (commit SHA ou tag de version), pas seulement `latest`.

## 4. Migrations base de données

Voir en détail : [database-migration-release-process.md](./database-migration-release-process.md). Résumé pour ce contexte :

- [ ] Les migrations Alembic à appliquer sont identifiées (`alembic history`).
- [ ] Un backup est pris **avant** toute migration en production (section 5).
- [ ] La fenêtre de maintenance est communiquée si la migration n'est pas rétrocompatible.

## 5. Sauvegardes

Avant tout déploiement touchant la base de données :

```bash
docker exec retines-postgresql pg_dump \
  -U retines \
  -d retines_db \
  --no-owner \
  --no-acl \
  -F c \
  -f /tmp/retines_backup_$(date +%Y%m%d_%H%M).dump
```

- [ ] Le dump est copié hors du serveur (poste local, stockage externe) — pas seulement laissé dans `/tmp`.
- [ ] Le dump précédent (avant ce déploiement) est conservé au moins 30 jours.

## 6. Déploiement — staging

- [ ] `git checkout main && git pull`
- [ ] `docker compose -f docker-compose.yml -f docker-compose.prod.yml pull` (ou `build`) sur le serveur staging
- [ ] `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`
- [ ] `docker compose exec backend alembic upgrade head`
- [ ] Smoke tests (section 8) exécutés sur staging et OK

## 7. Déploiement — production

- [ ] Déploiement automatique via GitHub Actions au push sur `main` (voir workflow `Deploy to Production` — `deploy.yml`), ou déploiement manuel équivalent si les secrets CI/CD ne sont pas encore configurés :

```bash
# Sur le serveur production
cd /srv/retines-pupilles
git pull origin main
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
docker compose exec backend alembic upgrade head
```

- [ ] Vérifier que le déploiement automatique (`deploy.yml`) a bien un historique d'exécutions réussies avant de considérer le pipeline fiable (au 2026-07-01, ce workflow n'avait jamais tourné — premier déploiement à traiter avec vigilance renforcée).

## 8. Smoke tests post-déploiement

- [ ] `curl https://app.retineetpupille.be/api/v1/health` → `{"status":"ok",...}`
- [ ] Connexion (login) fonctionne avec un compte de test.
- [ ] Une fiche client existante est consultable.
- [ ] `docker compose ps` : tous les services `healthy`/`running`, aucun `restarting` en boucle.
- [ ] Certificat HTTPS valide (Let's Encrypt via Traefik) : `curl -I https://app.retineetpupille.be` ne renvoie pas d'erreur de certificat.
- [ ] Logs applicatifs ne contiennent pas d'erreur au démarrage : `docker compose logs --tail=100 backend`.

## 9. Rollback

Si un smoke test échoue :

1. Revenir à l'image/commit précédent : `git checkout <commit-precedent> && docker compose up -d --build` (ou redéployer le tag Docker précédent s'il existe).
2. Si une migration a été appliquée et doit être annulée : `docker compose exec backend alembic downgrade -1` (uniquement si la migration est réversible — voir database-migration-release-process.md).
3. Si la base de données est corrompue ou incohérente : restaurer le dump pris à l'étape 5 :

```bash
docker exec -i retines-postgresql pg_restore \
  -U retines \
  -d retines_db \
  --no-owner \
  --no-acl \
  /tmp/retines_backup_AAAAMMJJ_HHMM.dump
```

4. Documenter l'incident dans `PROJECT_STATE.md` (section blocages) avant de retenter.

## 10. Vérifications post-déploiement / sign-off

- [ ] Smoke tests (section 8) tous verts.
- [ ] Allyson informée que l'application est à jour (si le déploiement change son usage quotidien).
- [ ] `PROJECT_STATE.md` mis à jour avec la date et le contenu du déploiement.
- [ ] Ancien backup (avant ce déploiement) toujours accessible pendant au moins 30 jours (voir section 5).
