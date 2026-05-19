# PROJECT_STATE.md — Rétines & Pupilles

> Fichier de suivi global du projet. Mis à jour par `opt-end` à chaque fin de session.
> Lu par `opt-start` à chaque début de session.

## Projet

**Nom :** Rétines & Pupilles
**Pour :** Allyson Hardy, optométriste — ED Optique Heusy (Belgique)
**Responsable technique :** Fabian Hardy
**Domaine :** retineetpupille.be
**Serveur actuel :** 204.168.202.176 (temporaire — migratable)

## Phases du projet

| Phase | Description | Statut |
|---|---|---|
| 0 — Fondations | Infra, docs, workflow, skills | 🟡 En cours |
| 1 — Foundation code | FastAPI skeleton, DB, Auth | ⬜ À faire |
| 2 — Core métier | Clients, prescriptions, import DBF | ⬜ À faire |
| 3 — Commercial | Commandes, fournisseurs, stock | ⬜ À faire |
| 4 — Deploy | DNS, Traefik, prod, migration | ⬜ À faire |

## Sprint actuel — Sprint 0 : Fondations

**Objectif :** Tout ce qui permet de coder proprement (infra doc, workflow, skills, docker)

### TASK-000 : Workflow Cowork ↔ Claude Code ✅
- Skills opt-start / opt-end créés
- TASKS.md avec Sprint 1 prêt
- Flux validé : Cowork supervise, Claude Code code via SSH

### TASK-INF-001 : Documentation complète 🟡
- ✅ docs/00-overview.md
- ✅ docs/architecture/stack.md
- ✅ docs/architecture/server.md
- ✅ docs/architecture/data-merge.md
- ✅ docs/dev/getting-started.md
- ✅ docs/dev/git-workflow.md
- ✅ docs/dev/env-variables.md
- ✅ docs/deploy/migration.md
- ✅ docs/deploy/backup.md
- ✅ docs/user/guide-allyson.md
- ⬜ Remplacer les `[DOMAIN]` restants → retineetpupille.be

### TASK-INF-002 : Infrastructure Docker + Traefik 🟡
- ✅ docker-compose.yml (base)
- ✅ docker-compose.dev.yml
- ✅ docker-compose.prod.yml
- ✅ traefik/docker-compose.yml
- ✅ traefik/traefik.yml
- ✅ traefik/setup.sh
- ✅ mkdocs.yml + mkdocs-docker-compose.yml
- ⬜ Exécution Traefik migration sur serveur 204.168.202.176

### TASK-INF-003 : Agent Monitor 🟡
- ✅ agent-monitor/monitor.py (dashboard SSE port 7777)
- ✅ agent-monitor/hooks/ (pre-tool, post-tool, stop)
- ✅ agent-monitor/claude-hooks-config.json
- ⬜ Déploiement sur VM dev (après install VMware)

### TASK-INF-004 : VM Dev VMware ⬜
- Guide créé dans docs/dev/getting-started.md
- Installation en cours côté Fabian (VMware Workstation Pro 26h1)
- Ubuntu Server 24.04, 4GB RAM, Bridged network, 40GB disk

### TASK-INF-005 : DNS O2switch ⬜
- Domaine : retineetpupille.be (O2switch)
- À faire : Zone Editor → A records (PAS nameserver change)
  - app.retineetpupille.be → 204.168.202.176
  - docs.retineetpupille.be → 204.168.202.176
  - www.retineetpupille.be → 204.168.202.176

## Sprint 1 — Foundation code (planifié)

Voir TASKS.md pour le détail :
- TASK-001 : FastAPI skeleton
- TASK-002 : React frontend
- TASK-003 : DB models + Alembic
- TASK-004 : JWT auth
- TASK-005 : DBF import service

## Décisions architecturales clés

| Décision | Justification | Date |
|---|---|---|
| Structure propre, EDOPT se greffe | Rétines & Pupilles a son propre modèle métier optimisé | 2026-05 |
| Merge 4 cas (source + allyson_modified_fields) | Protéger données saisies par Allyson | 2026-05 |
| Traefik remplace Nginx | Multi-projet sur même serveur, SSL auto | 2026-05 |
| Claude Code via SSH sur VM dev | Pas de code sur machine Windows Fabian | 2026-05 |
| MkDocs Material pour docs | Simple, versionnée Git, thème propre | 2026-05 |

## Informations métier (Allyson) — Questionnaire intégré ✅

> Synthèse complète dans `docs/user/reponses-allyson.md`

**Profil usage :**
- 5-10 clients/jour — volume modéré
- Consulte l'historique **systématiquement** avant chaque client → recherche rapide critique
- Accès hors magasin : rarement (1x/mois) → mobile non prioritaire pour MVP

**Champs client indispensables :** nom, prénom, date de naissance, GSM

**Priorités MVP (indispensables) :**
1. Gestion clients (création, modification, historique)
2. Recherche client rapide (nom, GSM, adresse)
3. Enregistrement prescriptions visionnelles
4. Stock & gestion fournisseurs
5. Commandes verres/montures
6. Facturation & documents commerciaux

**Scope confirmé :** optique uniquement (pas d'auditifs), inventaire annuel, lentilles sur commande

**Points à clarifier encore :**
- 🟡 A3 : quelles sont les 3 tâches les plus chronophages ? (champ non rempli)
- 🟡 A2 : flux détaillé d'une visite client ? (champ non rempli)
- 🟡 Multi-magasin (Heusy + Welkenraedt) : fréquence et besoin réel de synchro ?

## Blocages actuels

| Blocage | Ce qu'il faut | Priorité |
|---|---|---|
| ~~Réponses questionnaire Allyson~~ | ~~Fabian doit re-partager~~ | ✅ Levé |
| A3 & A2 non remplis | Poser les questions à Allyson | 🟡 Moyen |
| VM dev non installée | Fabian installe VMware + Ubuntu | 🟡 Moyen |
| DNS non configuré | Fabian → O2switch Zone Editor | 🟡 Moyen |
| GitHub repo non créé | Créer retines-pupilles + GitHub Actions | 🟡 Moyen |

## Dernière session — 2026-05-19

**Mode :** COWORK

### Réalisé
- Définition logique de fusion 4 cas (source + allyson_modified_fields)
- Mise à jour rapport Word (philosophie données)
- Documentation complète créée (10 fichiers docs/)
- Infrastructure Docker + Traefik configurée
- TASKS.md Sprint 1 rédigé
- Agent monitor (dashboar