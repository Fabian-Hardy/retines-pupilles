# Processus de release des migrations base de données — Rétines & Pupilles

> TASK-087. Document opérationnel uniquement — aucun comportement applicatif n'est modifié par ce fichier.
> Complète [production-deployment-checklist.md](./production-deployment-checklist.md) (section 4).

## Principes

- Les migrations sont gérées exclusivement par **Alembic**. Ne jamais modifier le schéma à la main (voir `CLAUDE.md`).
- Les migrations sont versionnées dans Git et **ne sont jamais modifiées après avoir été mergées** dans `develop` ou `main`. Une correction se fait via une nouvelle migration.
- Une migration doit rester **déterministe et réversible** dans la mesure du possible (règle `AGENTS.md`).
- Toute migration qui touche des données existantes (pas seulement le schéma) est traitée comme à risque et suit la procédure production ci-dessous même sur un petit changement.

## 1. Création d'une migration (local / dev)

```bash
docker compose exec backend alembic revision --autogenerate -m "description courte"
```

- [ ] Le fichier généré dans `backend/alembic/versions/` est relu intégralement (l'autogénération se trompe parfois, notamment sur les renommages de colonnes).
- [ ] `upgrade()` et `downgrade()` sont tous les deux implémentés et cohérents.
- [ ] Si la migration modifie des données (pas seulement le schéma), le `upgrade()` inclut le script de migration de données, pas seulement le DDL.

## 2. Revue de la migration (pull request)

- [ ] La PR contient uniquement une migration par changement logique (pas plusieurs migrations non liées dans la même PR).
- [ ] La revue vérifie explicitement :
  - la réversibilité (`downgrade()` ramène réellement à l'état précédent) ;
  - l'absence de perte de données silencieuse (ex: `DROP COLUMN` sur une colonne qui contient encore des données utiles) ;
  - les index et contraintes nécessaires sont présents (voir `CLAUDE.md` : index attendus sur `client.external_id`, `client.source`, etc.) ;
  - le temps d'exécution estimé sur un volume réaliste (voir section 6) si la table est volumineuse.

## 3. Validation locale / dev

```bash
# Appliquer
docker compose exec backend alembic upgrade head

# Vérifier l'idempotence : downgrade puis re-upgrade
docker compose exec backend alembic downgrade -1
docker compose exec backend alembic upgrade head

# Suite de tests complète
docker compose exec backend pytest tests/ -v
```

- [ ] `alembic upgrade head` passe sans erreur.
- [ ] `alembic downgrade -1` puis `alembic upgrade head` reproduit le même état (idempotence).
- [ ] La suite de tests passe après la migration.

## 4. Staging

- [ ] La migration est d'abord appliquée sur l'environnement staging, jamais directement en production.
- [ ] Un backup staging est pris avant (mêmes commandes qu'en production, section 6).
- [ ] Les smoke tests applicatifs (voir production-deployment-checklist.md, section 8) sont exécutés après la migration staging.
- [ ] Le temps d'exécution réel de la migration est noté, pour dimensionner la fenêtre de maintenance en production si la table est volumineuse.

## 5. Précautions avant une migration en production

- [ ] **Backup obligatoire** (section 6) — jamais de migration production sans dump récent vérifié.
- [ ] **Fenêtre de maintenance** : si la migration verrouille une table utilisée activement (peu probable vu le volume actuel du projet, mais à vérifier), prévenir Allyson et choisir un créneau hors utilisation (ex: en dehors des horaires du magasin).
- [ ] **Smoke tests** définis à l'avance : quelles requêtes/actions vérifier juste après la migration pour confirmer que tout fonctionne (ex: se connecter, consulter une fiche client, créer une prescription).
- [ ] La migration a déjà été validée avec succès sur staging (section 4).

## 6. Exécution en production

```bash
# 1. Backup avant migration
docker exec retines-postgresql pg_dump \
  -U retines \
  -d retines_db \
  --no-owner \
  --no-acl \
  -F c \
  -f /tmp/retines_backup_pre_migration_$(date +%Y%m%d_%H%M).dump

# 2. Vérifier l'état actuel des migrations
docker compose exec backend alembic current
docker compose exec backend alembic history

# 3. Appliquer
docker compose exec backend alembic upgrade head

# 4. Vérifier
docker compose exec backend alembic current
docker compose exec postgresql psql -U retines -d retines_db -c "\\dt"
```

- [ ] Le backup pré-migration est confirmé présent et de taille cohérente avant de lancer `upgrade head`.
- [ ] `alembic current` correspond bien à la révision attendue après exécution.
- [ ] Les smoke tests définis en section 5 sont exécutés immédiatement après.

## 7. Rollback d'une migration

- Si la migration est réversible et que le problème est détecté rapidement :

```bash
docker compose exec backend alembic downgrade -1
```

- Si la migration n'est pas proprement réversible, ou si des données ont déjà été modifiées de façon non triviale par l'application entre-temps : **restaurer le backup pris en section 6** plutôt que de tenter un `downgrade` risqué :

```bash
docker exec -i retines-postgresql pg_restore \
  -U retines \
  -d retines_db \
  --no-owner \
  --no-acl \
  /tmp/retines_backup_pre_migration_AAAAMMJJ_HHMM.dump
```

- [ ] Dans tous les cas, documenter l'incident dans `PROJECT_STATE.md` avant de retenter la migration.

## 8. Checklist pré/post migration (résumé)

**Avant :**
- [ ] Migration relue et testée en local (section 1-3)
- [ ] Validée sur staging (section 4)
- [ ] Backup production pris et vérifié (section 6)
- [ ] Smoke tests définis à l'avance (section 5)

**Après :**
- [ ] `alembic current` = révision attendue
- [ ] Smoke tests exécutés et verts
- [ ] Backup pré-migration conservé au moins 30 jours
- [ ] `PROJECT_STATE.md` mis à jour si la migration a un impact notable (nouvelle table, changement de champ obligatoire, etc.)
