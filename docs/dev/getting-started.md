# Setup du serveur de développement local (VMware)

## Principe

Le développement se fait sur une **VM Linux sous VMware sur le poste Windows de Fabian**. Cette VM est une réplique exacte de l'environnement de production — même Docker, même Docker Compose, mêmes images. La seule différence est le fichier d'override `docker-compose.dev.yml` qui active le hot reload et expose les ports de debug.

```
Poste Windows (Fabian)
└── VMware Workstation
    └── VM Ubuntu 24.04 (dev)
        └── Docker + Docker Compose
            ├── retines-backend (FastAPI, hot reload)
            ├── retines-frontend (Vite, hot reload)
            ├── postgres (dev DB)
            └── redis
```

Claude Code / agents dev travaillent **directement sur cette VM via SSH** — pas besoin de toucher Windows.

---

## Étape 1 — Créer la VM sous VMware

### Télécharger Ubuntu Server 24.04 LTS
```
https://ubuntu.com/download/server
→ Ubuntu Server 24.04.x LTS (amd64)
```

### Configuration VM recommandée

| Paramètre | Valeur |
|---|---|
| RAM | 4 GB minimum (8 GB recommandé) |
| vCPU | 2 minimum (4 recommandé) |
| Disque | 40 GB (thin provisioned) |
| Réseau | **Bridged** (la VM obtient une IP sur ton réseau local) |
| Nom VM | `retines-dev` |

> ⚠️ Utiliser le mode **Bridged** (pas NAT) pour que la VM soit accessible depuis le poste Windows et depuis Claude Code par SSH.

### Installation Ubuntu Server

1. Démarrer la VM avec l'ISO Ubuntu Server
2. Langue : **English** (évite les problèmes d'encodage dans les logs)
3. Keyboard : **French (Belgium)** ou selon préférence
4. Type d'installation : **Ubuntu Server (minimized)**
5. Réseau : laisser DHCP, noter l'IP assignée à la fin
6. Storage : **Use entire disk** (pas de LVM complexe pour une VM dev)
7. Profil :
   - Name : `fabian`
   - Server name : `retines-dev`
   - Username : `fabian`
   - Password : choisir un mot de passe solide
8. SSH : ✅ **Install OpenSSH server**
9. Snaps : décocher tout (on installe Docker manuellement)
10. Reboot et retirer l'ISO

---

## Étape 2 — Configuration de base de la VM

Se connecter en SSH depuis Windows :
```powershell
ssh fabian@[IP_VM]
```

### Mettre à jour le système
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl wget htop unzip
```

### Configurer une IP fixe (recommandé)

Éditer la config réseau :
```bash
sudo nano /etc/netplan/00-installer-config.yaml
```

Remplacer par :
```yaml
network:
  version: 2
  ethernets:
    ens33:  # vérifier le nom de l'interface avec: ip link show
      dhcp4: no
      addresses:
        - 192.168.1.200/24  # adapter à ton réseau local
      routes:
        - to: default
          via: 192.168.1.1   # adresse de ta box
      nameservers:
        addresses: [8.8.8.8, 1.1.1.1]
```

```bash
sudo netplan apply
```

### Ajouter la clé SSH de Fabian (et de Claude Code)

```bash
mkdir -p ~/.ssh
# Coller la clé publique depuis Windows
echo "ssh-ed25519 AAAA... fabian@windows" >> ~/.ssh/authorized_keys
# Ajouter aussi la clé publique de Claude Code (générée à l'étape 5)
chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys
```

---

## Étape 3 — Installer Docker

```bash
# Supprimer les vieilles versions si présentes
sudo apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null

# Installer Docker via script officiel
curl -fsSL https://get.docker.com | sudo sh

# Ajouter l'utilisateur au groupe docker (évite sudo à chaque commande)
sudo usermod -aG docker fabian

# Appliquer le groupe (ou déconnecter/reconnecter)
newgrp docker

# Vérifier
docker --version
docker compose version
```

### Configurer le swap (identique à la prod)

```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## Étape 4 — Cloner le repository

```bash
# Générer une clé SSH pour la VM dev (accès GitHub)
ssh-keygen -t ed25519 -C "retines-dev-vm" -f ~/.ssh/github_retines
cat ~/.ssh/github_retines.pub
# → Copier cette clé publique dans GitHub (Settings > SSH Keys)

# Configurer SSH pour GitHub
cat >> ~/.ssh/config << 'EOF'
Host github.com
  IdentityFile ~/.ssh/github_retines
  User git
EOF

# Cloner le repo
mkdir -p ~/projects
cd ~/projects
git clone git@github.com:fabianhardy/retines-pupilles.git
cd retines-pupilles
```

---

## Étape 5 — Lancer l'environnement de développement

### Créer le fichier .env.dev

```bash
cp .env.example .env.dev
nano .env.dev
# Remplir les valeurs (voir docs/dev/env-variables.md)
```

### Démarrer les services

```bash
# Démarrage complet avec hot reload
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Voir les logs en temps réel
docker compose logs -f backend
docker compose logs -f frontend
```

### Vérifier que tout tourne

```bash
docker compose ps
# Tous les services doivent être "Up"

# Test backend
curl http://localhost:8000/api/v1/health
# → {"status": "ok", "version": "x.x.x"}

# Frontend accessible sur
# → http://[IP_VM]:5173
```

---

## Étape 6 — Accès depuis Windows

Ajouter dans `C:\Users\ninif\.ssh\config` :

```
Host retines-dev
  HostName 192.168.1.200
  User fabian
  IdentityFile C:\Users\ninif\.ssh\id_ed25519
```

Accès rapide :
```powershell
ssh retines-dev
```

Accès à l'app depuis le navigateur Windows :
```
http://192.168.1.200:5173    ← frontend (Vite)
http://192.168.1.200:8000    ← backend API (FastAPI)
http://192.168.1.200:8000/docs  ← Swagger UI (doc API interactive)
```

---

## Différences dev vs prod

| Paramètre | Dev (VMware) | Prod (serveur) |
|---|---|---|
| Hot reload | ✅ Activé (volumes montés) | ❌ Désactivé (images buildées) |
| Ports exposés | `5173` (front), `8000` (back), `5432` (postgres) | Seuls 80/443 via Traefik |
| SSL | ❌ HTTP simple | ✅ HTTPS via Traefik + Let's Encrypt |
| Debug | ✅ Mode debug activé, logs verbeux | ❌ Mode production |
| .env | `.env.dev` (dans le repo `.gitignore`) | `.env.prod` (sur le serveur uniquement) |
| Base de données | DB locale isolée | DB prod avec vraies données Allyson |

---

## Commandes quotidiennes

```bash
# Démarrer
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Arrêter
docker compose down

# Voir les logs
docker compose logs -f [backend|frontend|postgresql]

# Lancer les tests
docker compose exec backend pytest tests/

# Créer une migration DB
docker compose exec backend alembic revision --autogenerate -m "description"
docker compose exec backend alembic upgrade head

# Accéder à la DB en direct
docker compose exec postgresql psql -U retines -d retines_db

# Reconstruire une image (après changement Dockerfile)
docker compose build backend
```
