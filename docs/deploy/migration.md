# Migration vers un nouveau serveur

## Contexte

Le serveur actuel (`204.168.202.176`) est temporaire. Quand Allyson reprendra la direction du magasin, Rétines & Pupilles migrera sur son propre serveur dédié.

**Durée estimée de la migration : 1 à 2 heures** (dont la majorité en attente de propagation DNS).

---

## Prérequis sur le nouveau serveur

- Ubuntu 24.04 LTS (ou toute distro avec Docker support)
- Docker + Docker Compose installés (même procédure que [getting-started.md](../dev/getting-started.md), Étapes 1-3)
- Accès SSH root (ou user avec sudo)
- Le domaine DNS reconfiguré vers la nouvelle IP

---

## Procédure de migration

### Étape 1 — Préparer le nouveau serveur

```bash
# Sur le nouveau serveur
sudo apt update && sudo apt upgrade -y
curl -fsSL https://get.docker.com | sudo sh

# Swap
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Créer la structure
sudo mkdir -p /srv/traefik /srv/retines-pupilles
```

### Étape 2 — Exporter les données PostgreSQL (sur l'ancien serveur)

```bash
# Sur l'ancien serveur
docker exec retines-postgresql pg_dump \
  -U retines \
  -d retines_db \
  --no-owner \
  --no-acl \
  -F c \
  -f /tmp/retines_backup_$(date +%Y%m%d_%H%M).dump

# Copier le dump vers le nouveau serveur
scp /tmp/retines_backup_*.dump root@[NOUVELLE_IP]:/tmp/
```

### Étape 3 — Copier la configuration (sur l'ancien serveur)

```bash
# Copier les fichiers Docker Compose et config Traefik
scp -r /srv/traefik root@[NOUVELLE_IP]:/srv/
scp /srv/retines-pupilles/docker-compose.yml root@[NOUVELLE_IP]:/srv/retines-pupilles/

# ⚠️ NE PAS copier .env.prod — le recréer manuellement sur le nouveau serveur
# pour éviter tout transit de secrets
```

### Étape 4 — Configurer le nouveau serveur

```bash
# Sur le nouveau serveur

# Créer le .env.prod (même valeurs que l'ancien, ou nouvelles si changement)
nano /srv/retines-pupilles/.env.prod

# Démarrer Traefik
cd /srv/traefik
docker compose up -d

# Démarrer l'app (sans les données encore)
cd /srv/retines-pupilles
docker compose up -d postgresql  # démarrer seulement la DB
```

### Étape 5 — Restaurer les données

```bash
# Sur le nouveau serveur, attendre que PostgreSQL soit healthy
docker compose exec postgresql pg_isready -U retines

# Restaurer le dump
docker exec -i retines-postgresql pg_restore \
  -U retines \
  -d retines_db \
  --no-owner \
  --no-acl \
  /tmp/retines_backup_*.dump

# Vérifier
docker compose exec postgresql psql -U retines -d retines_db \
  -c "SELECT COUNT(*) FROM clients;"
```

### Étape 6 — Démarrer l'application complète

```bash
cd /srv/retines-pupilles
docker compose up -d

# Vérifier la santé
docker compose ps
curl http://localhost:8000/api/v1/health
```

### Étape 7 — Basculer le DNS

Dans le panel O2switch d'Allyson :
- Modifier l'enregistrement A de `app.[DOMAIN]` : remplacer l'ancienne IP par la nouvelle
- Même chose pour `api.[DOMAIN]` si séparé

Attendre la propagation DNS (15 min à 4h). Tester depuis un browser en navigation privée.

### Étape 8 — Mettre à jour les secrets GitHub Actions

Dans GitHub → Settings → Secrets → Actions :
- Mettre à jour `PROD_SSH_HOST` avec la nouvelle IP
- Mettre à jour `PROD_SSH_KEY` si la clé SSH change

**Les futurs déploiements cibleront automatiquement le nouveau serveur.**

### Étape 9 — Vérification finale

```bash
# HTTPS fonctionne
curl https://app.[DOMAIN]/api/v1/health

# Allyson peut se connecter et voir ses données
# Les imports DBF fonctionnent
# Tester un import de fichier test
```

### Étape 10 — Désactiver l'ancien serveur

```bash
# Sur l'ancien serveur — arrêter l'app (garder le dump en backup)
cd /srv/retines-pupilles
docker compose down

# Conserver le dump PostgreSQL pendant 30 jours minimum avant suppression
```

---

## Checklist de migration

```
PRÉ-MIGRATION
[ ] Nouveau serveur provisionné et Docker installé
[ ] Nouveau serveur accessible en SSH
[ ] Domaine pointé vers la nouvelle IP (DNS propagé)
[ ] .env.prod recréé sur le nouveau serveur
[ ] Dump PostgreSQL effectué et vérifié (taille cohérente)

MIGRATION
[ ] Traefik démarré sur nouveau serveur
[ ] DB restaurée et vérifiée (COUNT des tables)
[ ] App démarrée et health check OK
[ ] HTTPS fonctionnel (certificat Let's Encrypt obtenu)
[ ] Allyson connectée et données visibles

POST-MIGRATION
[ ] Secrets GitHub Actions mis à jour
[ ] Test déploiement automatique depuis GitHub
[ ] Ancien serveur arrêté (pas supprimé avant 30j)
[ ] Dump conservé en backup offline
```

---

## Pourquoi la migration est simple

Tout est conçu pour ça :

- **100% Docker** : pas de dépendance au système hôte
- **Données dans PostgreSQL** : `pg_dump` / `pg_restore` sont fiables, éprouvés, universels
- **Config via .env** : pas de valeurs hardcodées dans le code
- **Traefik** : la config SSL et le routing se régénèrent automatiquement sur le nouveau serveur
- **GitHub comme source de vérité** : le code est sur GitHub, pas sur le serveur — `git pull` suffit

La seule donnée qui ne vit pas dans Git est le `.env.prod` (secrets) et la base PostgreSQL. Ces deux éléments sont gérés explicitement dans cette procédure.
