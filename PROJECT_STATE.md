# PROJECT_STATE.md — Rétines & Pupilles

> Fichier de suivi global du projet. Mis à jour par `opt-end` à chaque fin de session.
> Lu par `opt-start` à chaque début de session.

## Projet

**Nom :** Rétines & Pupilles
**Pour :** Allyson Hardy, optométriste — ED Optique Heusy (Belgique)
**Responsable technique :** Fabian Hardy
**Domaine :** retineetpupille.be
**Serveur actuel :** 204.168.202.176 (Hetzner — Traefik v3 opérationnel)

## Phases du projet

| Phase | Description | Statut |
|---|---|---|
| 0 — Fondations | Infra, docs, workflow, skills | ✅ Terminé |
| 1 — Foundation code | FastAPI skeleton, DB, Auth | 🟡 En cours |
| 2 — Core métier | Clients, prescriptions, import DBF | ⬜ À faire |
| 3 — Commercial | Commandes, fournisseurs, stock | ⬜ À faire |
| 4 — Deploy | DNS, prod, migration | ⬜ À faire |

## Sprint 0 — Fondations ✅ TERMINÉ (2026-05-19)

- ✅ VM dev Ubuntu 24.04 — Docker, Avahi, Tailscale (IP : 100.69.202.89)
- ✅ GitHub repo + branches main/develop + CI/CD GitHub Actions
- ✅ GitHub Secrets configurés (6 secrets)
- ✅ Documentation complète (docs/, CLAUDE.md, TASKS.md, ROADMAP.md, IDEAS.md)
- ✅ Réponses Allyson intégrées (docs/user/reponses-allyson.md)
- ✅ Traefik v3 déployé sur VPS — mind.fabianhardy.com migré, SSL Let's Encrypt auto
- ✅ /srv/retines-pupilles créé avec .env.prod (secrets générés)
- ✅ DNS Cloudflare : app/docs/www.retineetpupille.be → 204.168.202.176
- ✅ Tunnel Cowork↔VM via Tailscale opérationnel
- ✅ Source de vérité : VM/GitHub (OneDrive abandonné pour le code)

## Sprint 1 — Foundation code 🟡 EN COURS

- TASK-001 : FastAPI skeleton 🔴 **PROCHAINE TÂCHE**
- TASK-002 : React frontend 🔴
- TASK-003 : DB models + Alembic 🔴
- TASK-004 : JWT auth 🔴
- TASK-005 : DBF import service 🔴

## Accès VM dev depuis Cowork

- **IP Tailscale :** 100.69.202.89 / **User :** fabian / **Clé :** id_ed25519 (workspace)
- **Auth key Tailscale :** tailscale-authkey.txt (expire ~2026-08-17, Reusable+Ephemeral)
- Connexion via tailscaled userspace + SOCKS5 proxy localhost:1055

## Accès VPS prod

- **IP :** 204.168.202.176 / **User :** root / **Clé :** mind_hetzner (workspace)
- **Traefik :** /srv/traefik/ — fix clé : --providers.docker.network=traefik-public
- **Retines prod :** /srv/retines-pupilles/.env.prod (configuré)
- **Mind :** /srv/mind/ — migré sous Traefik (docker-compose.prod.yml + traefik.conf mis à jour)

## Décisions architecturales clés

| Décision | Justification | Date |
|---|---|---|
| Structure propre, EDOPT se greffe | Modèle métier optimisé optométrie | 2026-05 |
| Merge 4 cas (allyson_modified_fields) | Protéger données saisies par Allyson | 2026-05 |
| Traefik v3 + --providers.docker.network | Obligatoire si container multi-réseaux | 2026-05-19 |
| Claude Code via SSH sur VM dev | Pas de code sur Windows Fabian | 2026-05 |
| VM/GitHub = source de vérité | OneDrive abandonné pour le code | 2026-05-19 |

## Informations métier (Allyson)

> Synthèse complète dans docs/user/reponses-allyson.md

**Priorités MVP :** clients, recherche rapide, prescriptions, stock, commandes, facturation
**Champs requis :** nom, prénom, date_naissance, gsm
**À clarifier :** A3 (tâches chronophages), A2 (flux visite), multi-magasin

## Blocages actuels

| Blocage | Ce qu'il faut | Priorité |
|---|---|---|
| A3 & A2 non remplis | Poser les questions à Allyson | 🟡 Moyen |
| mind docker-compose.prod.yml modifié | Committer dans repo mind | 🟡 Faible |

## Dernière session — 2026-05-19 (session 3)

**Mode :** COWORK + infra

### Réalisé
- Tailscale VM dev + sandbox Cowork (auth key réutilisable, expire 2026-08-17)
- skill opt-start mis à jour (tunnel Tailscale intégré)
- IDEA-006 résolue — VM/GitHub = source de vérité
- /srv/retines-pupilles créé, .env.prod configuré
- GitHub Secrets configurés (6 secrets)
- Migration Traefik v3 — mind.fabianhardy.com SSL auto, fix --providers.docker.network
- Sprint 0 complété à 100%

### À faire prochaine session
- TASK-001 FastAPI skeleton
