# Stratégie de backup

## Principe

Les seules données irremplaçables sont dans PostgreSQL. Tout le reste (code, config) est dans GitHub.

**Backup quotidien automatique** : dump PostgreSQL → stockage cloud.

---

## Script de backup

Fichier `/srv/retines-pupilles/scripts/backup.sh` :

```bash
#!/bin/bash
set -e

TIMESTAMP=$(date +%Y%m%d_%H%M)
BACKUP_FILE="retines_backup_${TIMESTAMP}.dump"
BACKUP_DIR="/srv/retines-pupilles/backups"
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

# Dump PostgreSQL
docker exec retines-postgresql pg_dump \
  -U retines \
  -d retines_db \
  --no-owner --no-acl \
  -F c \
  -f "/tmp/${BACKUP_FILE}"

# Copier le dump localement
docker cp "retines-postgresql:/tmp/${BACKUP_FILE}" "${BACKUP_DIR}/${BACKUP_FILE}"

# Supprimer les backups de plus de RETENTION_DAYS jours
find "$BACKUP_DIR" -name "*.dump" -mtime "+${RETENTION_DAYS}" -delete

echo "[$(date)] Backup OK : ${BACKUP_FILE}"
```

## Planification (cron)

```bash
# Sur le serveur
crontab -e

# Backup quotidien à 2h du matin
0 2 * * * /srv/retines-pupilles/scripts/backup.sh >> /var/log/retines-backup.log 2>&1
```

## Vérifier que les backups tournent

```bash
tail -f /var/log/retines-backup.log
ls -lh /srv/retines-pupilles/backups/
```

## Restaurer un backup

```bash
# Choisir le fichier
ls /srv/retines-pupilles/backups/

# Restaurer
docker exec -i retines-postgresql pg_restore \
  -U retines -d retines_db --clean --no-owner \
  < /srv/retines-pupilles/backups/retines_backup_20260519_0200.dump
```
