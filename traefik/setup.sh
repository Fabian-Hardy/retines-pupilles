#!/usr/bin/env bash
# setup.sh — Initialisation de Traefik sur le serveur de production
# Serveur : 204.168.202.176
# Usage   : scp -r traefik/ root@204.168.202.176:/srv/traefik && ssh root@204.168.202.176 "bash /srv/traefik/setup.sh"

set -euo pipefail

echo "==> Création du répertoire Traefik..."
mkdir -p /srv/traefik

echo "==> Copie des fichiers de configuration (si pas déjà fait)..."
# Les fichiers traefik.yml et docker-compose.yml doivent être présents dans /srv/traefik/
if [ ! -f /srv/traefik/traefik.yml ]; then
  echo "ERREUR : /srv/traefik/traefik.yml manquant. Copiez les fichiers du dossier traefik/ d'abord."
  exit 1
fi

echo "==> Initialisation de acme.json (certificats Let's Encrypt)..."
touch /srv/traefik/acme.json
chmod 600 /srv/traefik/acme.json

echo "==> Création du réseau Docker 'proxy' (si inexistant)..."
docker network create proxy 2>/dev/null || true

echo "==> Démarrage de Traefik..."
cd /srv/traefik && docker compose up -d

echo "==> Vérification du statut..."
sleep 3
docker compose -f /srv/traefik/docker-compose.yml ps

echo ""
echo "Traefik démarré. Vérifier les logs avec :"
echo "  docker compose -f /srv/traefik/docker-compose.yml logs -f"
