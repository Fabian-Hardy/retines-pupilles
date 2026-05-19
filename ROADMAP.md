# ROADMAP — Rétines & Pupilles

> Document vivant. Mis à jour par `opt-end` à chaque décision qui impacte le phasing.
> Dernière mise à jour : 2026-05-19

---

## Principes directeurs

1. **Livrer tôt, livrer utile** — Allyson doit toucher quelque chose de réel le plus vite possible
2. **EDOPT se greffe sur notre structure, pas l'inverse** — le modèle de données est celui de l'optométrie moderne
3. **Le modèle de données anticipe l'avenir** — les champs pour stock réel, multi-site, multi-user sont prévus dès Sprint 1, même si l'UI ne les expose pas encore
4. **Portabilité absolue** — tout passe par `.env`, rien ne dépend du serveur hôte

---

## Phase 0 — Fondations *(en cours)*

**Objectif :** Tout ce qui permet de coder proprement. Pas de feature utilisateur.

| Tâche | Statut | Notes |
|---|---|---|
| Documentation complète (docs/) | ✅ Done | 10 fichiers |
| Docker + Traefik config | ✅ Done | 3 compose files |
| TASKS.md + workflow Cowork/CC | ✅ Done | Sprint 1 prêt |
| Skills opt-start / opt-end | ✅ Done | Installables |
| IDEAS.md + ROADMAP.md | ✅ Done | Ce fichier |
| GitHub repository | 🔴 À faire | Nom : retines-pupilles |
| VM dev VMware (Ubuntu 24.04) | 🟡 En cours | IP : 172.20.21.120 |
| SSH + Docker sur VM dev | 🔴 À faire | Après install VM |
| Agent monitor sur VM dev | 🔴 À faire | Port 7777 |
| Traefik migration sur serveur prod | 🔴 À faire | 204.168.202.176 |
| DNS O2switch (A records) | 🔴 À faire | app/docs/www → 204.168.202.176 |

---

## Phase 1 — Noyau MVP *(Sprint 1)*

**Objectif :** Allyson peut créer un client, enregistrer une prescription, chercher un client. C'est tout. C'est déjà énorme.

**Décision 2026-05-19 :** On réduit le Sprint 1 au noyau dur (login + clients + prescriptions). Stock/commandes/facturation passent en Phase 2.

| TASK | Description | Priorité |
|---|---|---|
| TASK-001 | Structure backend FastAPI | 🔴 Bloquant |
| TASK-002 | Structure frontend React | 🔴 Bloquant |
| TASK-003 | Modèles DB + Alembic | 🔴 Bloquant |
| TASK-004 | Auth JWT (Fabian + Allyson) | 🔴 Bloquant |
| TASK-005 | Import DBF initial (EDOPT → DB) | 🟡 Important |
| TASK-006 | CRUD Clients + recherche rapide | 🔴 Core MVP |
| TASK-007 | CRUD Prescriptions optométriques | 🔴 Core MVP |
| TASK-008 | Interface recherche client (< 3 clics) | 🔴 Core MVP |

**Critère de fin de Phase 1 :** Allyson peut se connecter, trouver un client en 3 clics, voir ses prescriptions, en ajouter une nouvelle.

**Durée estimée :** 4-6 semaines (sessions Cowork + Claude Code)

---

## Phase 2 — Opérationnel *(Sprint 2)*

**Objectif :** Allyson peut faire son travail quotidien complet dans l'app.

| Fonctionnalité | Notes |
|---|---|
| Catalogue articles (montures, verres, lentilles) | Avec `quantite_stock` nullable — stocké dès Phase 1, UI ici |
| Commandes verres/montures | Lien client → prescription → commande |
| Facturation simple (facture + reçu) | Deux types de documents |
| Remises ponctuelles | Fidélité, promo — montant ou % |
| Documents mutuelle | PDF pré-rempli pour le client |
| Détection doublons clients | Alerte fuzzy match, pas de merge auto |
| Import DBF périodique | Merge 4 cas, avec rapport |

**Durée estimée :** 6-8 semaines après Phase 1

---

## Phase 3 — Enrichissement *(Sprint 3)*

**Objectif :** L'app devient proactive et intelligente.

| Fonctionnalité | Notes |
|---|---|
| Rappels renouvellement prescription | Cron quotidien, notification in-app |
| Stock temps réel | Mouvements, alertes réapprovisionnement |
| Statistiques | Clients actifs, ventes, produits populaires |
| Export Excel/CSV/PDF | Pour comptable et reporting |
| Interface mobile (responsive) | Allyson accède depuis le téléphone 1x/mois |

---

## Phase 4 — Pérennité *(Sprint 4)*

**Objectif :** L'app est solide pour la reprise future du magasin.

| Fonctionnalité | Notes |
|---|---|
| Multi-utilisateurs avec droits | Rôles : admin (Fabian), optométriste (Allyson), vendeur |
| Synchronisation multi-magasin | Si Welkenraedt devient pertinent |
| Intégration comptable | Export format comptable belge |
| Migration vers nouveau serveur | Procédure documentée dans deploy/migration.md |
| Sauvegarde automatique | Script cron + vérification d'intégrité |

---

## Hors scope (décisions fermes)

| Élément | Raison |
|---|---|
| Appareils auditifs | Allyson : "Non" — hors métier |
| Envoi direct à la mutuelle | Allyson prépare les docs, le client envoie |
| Application mobile native | Web responsive suffit pour l'usage actuel |
| GraphQL | Pas justifié pour ce volume |
| Microservices | Over-engineering pour 1-2 utilisateurs |

---

## Journal des décisions de phasing

| Date | Décision | Justification |
|---|---|---|
| 2026-05-19 | Sprint 1 réduit au noyau (clients + prescriptions) | Livrer vite quelque chose d'utile plutôt que tout en même temps |
| 2026-05-19 | Stock UI en Phase 2, modèle DB en Phase 1 | Le champ `quantite_stock` existe dès la migration initiale |
| 2026-05-19 | Multi-magasin : champ `site` en DB Phase 1, UI Phase 4 | Facile à ajouter maintenant, pénible à retrofitter |
| 2026-05-19 | Stack gardée telle quelle (Redis, FastAPI async, React 19) | Investissement long terme pour la future reprise du magasin |
