# Infrastructure serveur

## Contexte : serveur temporaire

> ⚠️ Le serveur actuel (`204.168.202.176`) est un serveur personnel de Fabian hébergeant plusieurs projets. Rétines & Pupilles est conçu pour en partir facilement. Quand Allyson reprendra la direction du magasin, l'application migrera sur son propre serveur. **Voir [Procédure de migration](../deploy/migration.md).**

---

## Serveur actuel

| Paramètre | Valeur |
|---|---|
| IP | `204.168.202.176` |
| OS | Ubuntu 24.04 LTS |
| CPU | 4 vCPU Intel Xeon |
| RAM | 7.6 GB |
| Disque | 38 GB (15 GB libres) |
| Docker | 29.5.1 |
| Docker Compose | v5.1.3 |
| Accès SSH | `root@204.168.202.176` (clé `mind_hetzner`) |

---

## Projets cohabitants

| Projet | Répertoire | Domaine | Réseau Docker |
|---|---|---|---|
| `mind` | `/srv/mind/` | `mind.fabianhardy.com` | `mind-prod-net` |
| `retines-pupilles` | `/srv/retines-pupilles/` | `app.[DOMAIN]` | `retines-net` |
| Traefik (partagé) | `/srv/traefik/` | — | `proxy` (partagé) |

---

## Architecture réseau Docker

```
                    ┌──────────────────────────────┐
Internet ──────────▶│  Traefik  (réseau: proxy)    │
                    │  ports 80, 443               │
                    └───────────┬──────────────────┘
                                │ réseau proxy
              ┌─────────────────┴──────────────────┐
              │                                     │
   ┌──────────▼──────────────┐     ┌───────────────▼──────────────┐
   │  mind-nginx             │     │  retines-frontend             │
   │  (réseau: mind-prod-net)│     │  (réseau: proxy + retines-net)│
   └──────────┬──────────────┘     └───────────────┬──────────────┘
              │ mind-prod-net                        │ retines-net
   ┌──────────▼──────────────┐     ┌───────────────▼──────────────┐
   │  mind-app (PHP)         │     │  retines-backend (FastAPI)    │
   │  mind-postgresql        │     │  retines-postgresql           │
   │  mind-redis             │     │  retines-redis                │
   │  mind-ollama ◀──────────┼─────┼── (réseau ollama-net partagé) │
   └─────────────────────────┘     └──────────────────────────────┘
```

**Règles d'isolation :**
- Chaque projet a son propre réseau Docker interne — les bases de données ne sont jamais joignables depuis un autre projet.
- Seul Traefik est sur le réseau `proxy` et peut atteindre les frontends/backends des deux projets.
- Ollama est accessible depuis les deux projets via un réseau `ollama-net` dédié.
- Aucun port de base de données n'est exposé à l'extérieur.

---

## Structure fichiers sur le serveur

```
/srv/
├── traefik/
│   ├── docker-compose.yml
│   ├── traefik.yml          ← config statique Traefik
│   └── acme.json            ← certificats Let's Encrypt (chmod 600)
├── mind/                    ← projet existant (inchangé fonctionnellement)
│   ├── docker-compose.yml
│   ├── docker-compose.prod.yml
│   └── .env.prod
└── retines-pupilles/
    ├── docker-compose.yml
    └── .env.prod            ← jamais dans Git (secrets)
```

---

## Traefik — configuration

### Pourquoi Traefik et pas Nginx comme proxy global ?

Le projet `mind` utilise actuellement Nginx sur les ports 80/443. Ajouter un deuxième projet avec son propre domaine est impossible sans conflit de ports. Traefik résout ça nativement :
- Un seul processus écoute sur 80/443
- Le routing se configure via des **labels Docker** sur chaque container
- SSL Let's Encrypt géré automatiquement, sans Certbot externe
- Zero downtime sur les déploiements

### Migration mind → Traefik (one-time)

La migration consiste à :
1. Déployer Traefik sur le réseau `proxy`
2. Retirer les ports 80/443 de `mind-nginx`
3. Ajouter les labels Traefik sur `mind-nginx`
4. Vérifier que `mind.fabianhardy.com` fonctionne toujours
5. Ajouter `retines-pupilles` avec ses propres labels

### Labels Traefik type (retines-pupilles backend)

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.retines-api.rule=Host(`app.[DOMAIN]`) && PathPrefix(`/api`)"
  - "traefik.http.routers.retines-api.tls=true"
  - "traefik.http.routers.retines-api.tls.certresolver=letsencrypt"
  - "traefik.http.services.retines-api.loadbalancer.server.port=8000"
  - "traefik.docker.network=proxy"
```

---

## Domaine — DNS O2switch

Le domaine d'Allyson est hébergé chez **O2switch** (panel cPanel).

### Enregistrements DNS à créer

| Type | Nom | Valeur | TTL |
|---|---|---|---|
| A | `app.[DOMAIN]` | `204.168.202.176` | 3600 |
| A | `api.[DOMAIN]` | `204.168.202.176` | 3600 |
| A | `www.[DOMAIN]` | `204.168.202.176` | 3600 (future site vitrine) |

**Procédure O2switch :**
1. Connecter au panel cPanel d'O2switch
2. Section "Zone Editor" ou "Éditeur de zones DNS"
3. Sélectionner le domaine
4. Ajouter chaque enregistrement A ci-dessus
5. Propagation DNS : 15 minutes à 4 heures

> Note : Si le domaine est en mode "parking" chez O2switch, vérifier qu'il n'y a pas de redirection active qui écraserait les enregistrements A.

---

## Ollama — modèles disponibles

| Modèle | Taille | Usage prévu |
|---|---|---|
| `llama3.2:3b` | 2.0 GB | Déjà installé. Aide à la saisie, suggestions, détection anomalies prescriptions. |

Ollama est accessible depuis le backend via : `http://ollama:11434/api/generate`

Pour ajouter un modèle :
```bash
docker exec mind-ollama-1 ollama pull llama3.2:8b
```

---

## Sécurité serveur

| Mesure | État |
|---|---|
| Accès SSH par clé uniquement | ✅ En place |
| Ports DB non exposés | ✅ En place (réseau Docker interne uniquement) |
| SSL/TLS | ✅ Via Traefik + Let's Encrypt |
| Fail2ban | 🔄 À configurer |
| Swap | 🔄 À configurer (0 actuellement — risque OOM sous charge) |
| Backup PostgreSQL automatique | 🔄 À configurer |

### Ajouter le swap (commande)

```bash
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

---

## Monitoring

Pour ce stade du projet, monitoring minimaliste :
- **Portainer** (optionnel) : interface web pour voir les containers en cours, logs
- **Traefik dashboard** : état des routes et certificats SSL

Pas de stack ELK ou Prometheus pour le MVP — surengineering.
