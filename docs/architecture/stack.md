# Architecture technique — Choix de stack

## Vue d'ensemble

```
┌─────────────────────────────────────────────┐
│              Navigateur / App web            │
└──────────────────────┬──────────────────────┘
                       │ HTTPS
┌──────────────────────▼──────────────────────┐
│              Traefik (reverse proxy)         │
│         SSL Let's Encrypt automatique        │
└──────────────────────┬──────────────────────┘
          ┌────────────┴────────────┐
          │                         │
┌─────────▼────────┐    ┌──────────▼────────┐
│  Frontend        │    │  Backend API       │
│  React + Vite    │    │  Python + FastAPI  │
│  TypeScript      │    │  TypeScript strict │
└──────────────────┘    └──────────┬────────┘
                                   │
              ┌────────────────────┼───────────────┐
              │                    │               │
   ┌──────────▼──────┐  ┌─────────▼──────┐  ┌─────▼──────┐
   │  PostgreSQL 16  │  │   Redis 7       │  │  Ollama     │
   │  Base de données│  │  Cache/Sessions │  │  IA locale  │
   └─────────────────┘  └────────────────┘  └────────────┘
```

---

## Composants et justifications

### Backend : Python + FastAPI

**Choix retenu :** Python 3.12 + FastAPI + Pydantic v2

**Pourquoi Python et pas Node.js/PHP :**
- **Traitement des fichiers dBASE (.DBF)** : la librairie `dbfread` (Python) est mature et directement utilisable pour l'import des données EDOPT. Pas d'équivalent fiable en Node.
- **Typage fort avec Pydantic** : validation automatique de toutes les données médicales (prescriptions optométriques, ordonnances) avec des schémas déclarés explicitement. Les erreurs sont détectées à la frontière, pas au fond de la logique métier.
- **FastAPI** : framework async natif, performances excellentes, génération automatique de documentation OpenAPI/Swagger (utilisée pour typer automatiquement le client frontend).
- **Préparation IA/ML** : l'analyse future des prescriptions (tendances, détection anomalies) sera triviale en Python. En Node, ce serait une dépendance externe complexe.
- **SQLAlchemy 2.0 async + Alembic** : ORM mature, migrations versionnées, requêtes SQL explicites quand besoin (pas de magic).

**Organisation backend :**
```
backend/
├── app/
│   ├── api/           ← routes FastAPI (versionnées /api/v1/)
│   ├── core/          ← config, sécurité, middleware, JWT
│   ├── db/
│   │   ├── models/    ← modèles SQLAlchemy
│   │   └── migrations/ ← fichiers Alembic
│   ├── schemas/       ← Pydantic schemas (validation I/O)
│   └── services/      ← logique métier (import DBF, merge, prescriptions)
├── tests/
│   ├── unit/          ← tests logique pure (merge, validation)
│   └── integration/   ← tests endpoints API
├── Dockerfile
├── pyproject.toml     ← dépendances (uv ou pip)
└── alembic.ini
```

---

### Frontend : React + TypeScript + Vite

**Choix retenu :** React 19 + TypeScript strict + Vite + TailwindCSS

**Pourquoi :**
- **React** : écosystème riche, composants réutilisables, migration future vers Next.js (SSR) sans réécriture si le site vitrine se connecte à l'app.
- **TypeScript strict** : le client API est généré automatiquement depuis la spec OpenAPI du backend (outil `openapi-ts`). Les types sont partagés sans effort manuel.
- **Vite** : build ultra-rapide, hot reload instantané en dev.
- **TailwindCSS** : pas de CSS à maintenir, cohérence visuelle garantie.
- **Zustand** : gestion d'état légère (pas de Redux — surengineering pour ce périmètre).

**Organisation frontend :**
```
frontend/
├── src/
│   ├── api/           ← client typé généré depuis OpenAPI
│   ├── components/    ← composants réutilisables
│   ├── pages/         ← vues (clients, prescriptions, import, etc.)
│   ├── stores/        ← état global Zustand
│   └── utils/
├── public/
├── Dockerfile
├── vite.config.ts
└── package.json
```

---

### Base de données : PostgreSQL 16

**Pourquoi PostgreSQL et pas MySQL/SQLite :**
- Relations fortes entre clients ↔ prescriptions ↔ commandes ↔ factures — PostgreSQL est conçu pour ça.
- Support JSON natif (utile pour stocker les champs libres sans migration lourde).
- `pg_dump` / `pg_restore` fiables pour les migrations de serveur.
- SQLite : pas adapté à une app web (verrous en écriture, pas de migrations robustes).

---

### Redis 7

Utilisé pour :
- Cache des sessions JWT (révocation possible)
- File d'attente légère pour les imports DBF lourds (évite les timeouts HTTP)

---

### Ollama (déjà en place sur le serveur)

- Modèle actuel : `llama3.2:3b`
- Accessible depuis le backend via `http://ollama:11434` sur le réseau Docker interne
- Usage prévu : suggestions, détection d'anomalies dans les prescriptions, aide à la saisie
- **Non critique pour le MVP** — préparé mais pas activé d'emblée

---

### Traefik v3 (reverse proxy)

- Gestion SSL Let's Encrypt automatique (renouvellement sans cron manuel)
- Routing par labels Docker — pas de fichier de config à maintenir par domaine
- Dashboard intégré pour monitorer les routes
- Remplace le Nginx + Certbot actuellement en place sur le serveur

---

## Décisions d'architecture clés

### API REST versionnée

Tous les endpoints sous `/api/v1/`. Quand une évolution cassante est nécessaire, on ajoute `/api/v2/` sans casser les clients existants.

### Génération automatique du client API

FastAPI génère un schéma OpenAPI. L'outil `openapi-ts` génère automatiquement le client TypeScript du frontend. Résultat : **zéro désynchronisation possible entre back et front** — si un endpoint change, le frontend ne compile plus jusqu'à mise à jour.

```bash
# Commande à lancer après chaque changement d'API
npm run generate:api
```

### Authentification JWT

- Access token : 15 minutes (court pour limiter l'exposition)
- Refresh token : 7 jours, stocké en cookie `httpOnly` (inaccessible au JS, protège contre XSS)
- Révocation possible via Redis (blacklist des tokens révoqués)

### Migrations de base de données

**Règle absolue : on ne modifie jamais le schéma à la main.**

Toute modification de schéma passe par une migration Alembic :
```bash
alembic revision --autogenerate -m "add_field_prescription_prism"
alembic upgrade head
```

Les migrations sont versionnées dans Git. La DB en prod est toujours dans un état connu et reproductible.

---

## Ce qui n'est PAS dans cette stack (et pourquoi)

| Technologie | Raison d'exclusion |
|---|---|
| GraphQL | Surengineering pour ce périmètre. REST + OpenAPI est suffisant et plus simple à maintenir. |
| MongoDB | Relations fortes entre les données optométriques → base relationnelle obligatoire. |
| Next.js (pour MVP) | SSR non nécessaire pour une app interne mono-utilisateur. Prévu pour la phase site vitrine. |
| Kubernetes | Surengineering. Docker Compose est suffisant et bien plus simple à migrer sur un nouveau serveur. |
| Microservices | Un seul service backend. La séparation en micro-services se justifie à partir de plusieurs équipes ou charges très différentes. |
