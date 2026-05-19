# Mise en place infra technique — Rétines & Pupilles

> Ordre d'exécution à suivre une fois la VM Ubuntu installée.
> Fabian exécute les étapes marquées 🧑 — Claude Code exécute les étapes marquées 🤖.

---

## Étape 1 — Finaliser l'installation Ubuntu (VM) 🧑

Depuis l'écran d'installation Ubuntu Server :

```
# Réseau : sélectionner ens33, DHCP activé
# IP attribuée : 172.20.21.120 (vérifier après démarrage)

# Pas de LVM, pas de RAID
# Installer OpenSSH server : OUI
# Aucun snap à installer
```

Après le premier boot :
```bash
# Sur la VM
sudo apt update && sudo apt upgrade -y
sudo hostnamectl set-hostname retines-dev

# Vérifier l'IP
ip addr show ens33
```

---

## Étape 2 — SSH depuis Windows 🧑

Sur ta machine Windows, éditer `C:\Users\ninif\.ssh\config` :

```
Host retines-dev
    HostName 172.20.21.120
    User [ton-user-ubuntu]
    IdentityFile C:\Users\ninif\.ssh\id_rsa
    ServerAliveInterval 60
```

Tester :
```powershell
ssh retines-dev
```

---

## Étape 3 — Docker sur la VM 🤖 (via SSH)

```bash
# Install Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker

# Vérifier
docker --version
docker compose version

# Swap 4GB (si pas déjà fait)
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## Étape 4 — Créer le repository GitHub 🧑

1. Aller sur https://github.com/new
2. Nom : `retines-pupilles`
3. Private : ✅
4. Ajouter Fabian comme owner
5. Ne pas initialiser avec README (on pousse le contenu existant)

Puis depuis la VM :
```bash
mkdir -p ~/projects
cd ~/projects
git clone git@github.com:[username]/retines-pupilles.git
cd retines-pupilles
```

---

## Étape 5 — Pousser la doc existante vers GitHub 🧑 + 🤖

Les fichiers sont actuellement dans `C:\Users\ninif\OneDrive\Projet ED\ED Optique\retines-pupilles-docs\`.

Option A — Push depuis Windows PowerShell :
```powershell
cd "C:\Users\ninif\OneDrive\Projet ED\ED Optique\retines-pupilles-docs"
git init
git remote add origin git@github.com:[username]/retines-pupilles.git
git add .
git commit -m "chore: initial project setup — docs, docker, skills"
git branch -M main
git push -u origin main
```

Option B — Fabian copie les fichiers sur la VM via SCP, puis push depuis la VM.

---

## Étape 6 — Cloner sur la VM et vérifier Docker Compose 🤖

```bash
cd ~/projects/retines-pupilles
cp .env.example .env.dev
# Éditer .env.dev avec les vraies valeurs

# Démarrer l'environnement dev
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Vérifier
docker compose ps
curl http://localhost:8000/api/v1/health
```

---

## Étape 7 — Agent Monitor sur la VM 🤖

```bash
cd ~/projects/retines-pupilles/agent-monitor

# Installer les dépendances Python
pip3 install --user requests

# Lancer le monitor en background
nohup python3 monitor.py > /tmp/monitor.log 2>&1 &
echo $! > /tmp/monitor.pid

# Vérifier
curl http://localhost:7777/health
```

Configurer les hooks Claude Code (depuis la VM, dans `~/.claude/`) :
```bash
mkdir -p ~/.claude/hooks
cp agent-monitor/hooks/*.sh ~/.claude/hooks/
chmod +x ~/.claude/hooks/*.sh

# Ajouter la config hooks dans ~/.claude/settings.json
# (copier le contenu de agent-monitor/claude-hooks-config.json)
```

Accéder au dashboard depuis Windows : `http://172.20.21.120:7777`

---

## Étape 8 — GitHub Secrets pour CI/CD 🧑

Dans GitHub → Settings → Secrets → Actions :

```
PROD_SERVER_HOST = 204.168.202.176
PROD_SERVER_USER = root
PROD_SERVER_SSH_KEY = [contenu de mind_hetzner]
PROD_SERVER_PATH = /srv/retines-pupilles
SECRET_KEY = [openssl rand -hex 32]
POSTGRES_PASSWORD = [openssl rand -hex 16]
```

---

## Étape 9 — Traefik migration sur le serveur prod 🤖

> ⚠️ À faire APRÈS que l'environnement dev fonctionne et qu'au moins une tâche est DONE.

```bash
# Sur le serveur 204.168.202.176
ssh root@204.168.202.176

# Copier les fichiers Traefik
scp -r retines-pupilles-docs/traefik/ root@204.168.202.176:/srv/

# Exécuter le script de setup
chmod +x /srv/traefik/setup.sh
/srv/traefik/setup.sh

# Vérifier que Traefik est up
docker ps | grep traefik
curl -I http://localhost  # doit rediriger vers HTTPS
```

---

## Étape 10 — DNS O2switch 🧑

1. Aller sur https://www.o2switch.fr → cPanel → Zone Editor
2. Sélectionner `retineetpupille.be`
3. Ajouter 3 enregistrements A :

| Nom | Type | Valeur | TTL |
|---|---|---|---|
| app | A | 204.168.202.176 | 14400 |
| docs | A | 204.168.202.176 | 14400 |
| www | A | 204.168.202.176 | 14400 |

4. Attendre la propagation DNS (5-30 minutes)
5. Vérifier : `nslookup app.retineetpupille.be`

---

## Étape 11 — Fichier hosts Windows pour dev 🧑

Éditer `C:\Windows\System32\drivers\etc\hosts` en admin :

```
172.20.21.120   app.retineetpupille.dev
172.20.21.120   docs.retineetpupille.dev
172.20.21.120   api.retineetpupille.dev
```

Cela permet d'accéder aux services de la VM dev par nom de domaine depuis ton navigateur Windows.

---

## Checklist finale

- [ ] VM Ubuntu 24.04 installée et accessible via SSH
- [ ] Docker + Docker Compose installés sur la VM
- [ ] Swap 4GB configuré
- [ ] GitHub repository créé et doc poussée
- [ ] `docker compose up` fonctionne sur la VM dev
- [ ] Agent monitor accessible sur http://172.20.21.120:7777
- [ ] GitHub Secrets configurés
- [ ] Traefik déployé sur prod (204.168.202.176)
- [ ] DNS O2switch configuré (app/docs/www)
- [ ] Hosts Windows mis à jour pour dev
