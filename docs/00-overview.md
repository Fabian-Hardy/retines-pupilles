# Rétines & Pupilles — Vue d'ensemble du projet

## Qu'est-ce que c'est ?

**Rétines & Pupilles** est un logiciel de gestion métier (mini ERP/CRM) conçu spécifiquement pour **Allyson**, opticienne-optométriste au magasin ED Optique à Heusy (Belgique).

C'est un outil **personnel et autonome** — il ne remplace pas le système de gestion du magasin utilisé par les collègues, mais fonctionne en parallèle, en restant ancré dans les mêmes données via un mécanisme d'import et de fusion intelligent.

---

## Pourquoi ce projet ?

Le système actuel du magasin (EDOPT, MS-DOS, années 1990) est obsolète :
- Interface non utilisable sur appareils modernes
- Données isolées en fichiers locaux dBASE (.DBF)
- Pas de sauvegarde fiable
- Pas d'accès web ou mobile
- Impossible à étendre

Allyson travaille dans ce magasin comme salariée, avec l'ambition à terme d'en reprendre la direction. Rétines & Pupilles lui permet dès maintenant de gérer ses clients et prescriptions dans un outil moderne, sans dépendre de la décision collective d'investir dans un nouveau système pour tout le magasin.

---

## Acteurs

| Personne | Rôle |
|---|---|
| **Allyson Hardy** | Utilisatrice unique du logiciel. Opticienne-optométriste, ED Optique Heusy. |
| **Fabian Hardy** | Développeur et responsable technique du projet. Valide les livraisons avant mise en production. |
| **Collègues ED Optique** | Non-utilisateurs de Rétines & Pupilles. Continuent d'utiliser le système en place. Leur DB est la source de données principale via exports périodiques. |

---

## Principe de fonctionnement

### Import initial
Allyson importe la dernière version de la base de données principale du magasin (clients, prescriptions, historique) pour démarrer avec des données réelles et à jour.

### Enrichissement local
Elle encode ses propres clients, enrichit les fiches existantes, saisit les prescriptions et commandes au quotidien. L'application trace la **provenance de chaque donnée** (source DB principale ou saisie par Allyson).

### Indépendance
Les collègues continuent d'utiliser leur système sans changement. Allyson continue de communiquer avec eux comme elle le fait actuellement — Rétines & Pupilles n'impose pas de flux d'export vers les collègues.

### Fusion périodique
Quand Allyson reçoit un nouveau fichier de la DB principale, l'application fusionne intelligemment :

| Cas | Comportement |
|---|---|
| Nouvel enregistrement dans la DB principale | Ajout automatique |
| Enregistrement existant, non modifié par Allyson | Mise à jour libre |
| Enregistrement existant, modifié par Allyson | Fusion champ par champ — ses données sont protégées |
| Enregistrement créé par Allyson | Jamais touché par les imports |

Un résumé est affiché après chaque import : *"32 nouveaux clients, 8 mis à jour, 3 conflits à résoudre"*.

---

## Contraintes clés

### Portabilité obligatoire
Ce logiciel est hébergé sur un serveur personnel temporaire. Quand Allyson reprendra la direction du magasin, l'application devra migrer sur son propre serveur. **Toute l'infrastructure est conçue pour être intégralement portable** :
- Stack 100% Docker Compose
- Zéro dépendance au serveur hôte (pas de services système, pas de chemins hardcodés)
- Configuration via variables d'environnement uniquement
- Migration = dump PostgreSQL + `docker compose up` sur le nouveau serveur

Voir : [Procédure de migration](../deploy/migration.md)

### Usage solo
L'application est conçue pour **un seul utilisateur actif** (Allyson). Pas de gestion multi-utilisateurs dans le MVP. L'authentification est simple (login/mot de passe).

### Évolutivité future
L'architecture est pensée pour permettre ultérieurement :
- Connexion avec un site web vitrine (même domaine, sous-domaines séparés)
- Ajout d'un second utilisateur (collègue ou associé si reprise)
- Connexion à des services externes (comptabilité, mutuelles)
- Intégration IA/ML sur les données de prescriptions (Ollama déjà en place sur le serveur)

---

## Périmètre du MVP (version initiale)

| Module | Description | Priorité MVP |
|---|---|---|
| Authentification | Login sécurisé, session JWT | ✅ MVP |
| Gestion clients | Création, modification, recherche, historique | ✅ MVP |
| Prescriptions | Saisie complète (OD/OG, sphère, cylindre, axe, add, EP) | ✅ MVP |
| Import DBF | Import fichier DB principale + fusion intelligente | ✅ MVP |
| Commandes verres/montures | Lier prescription → commande, suivi état | ✅ MVP |
| Facturation | Création factures/reçus PDF | ✅ MVP |
| Stock basique | Catalogue montures et verres | ✅ MVP |
| Rappels | Renouvellement ordonnance, livraison en attente | 🔄 Post-MVP |
| Statistiques | CA, produits populaires, fidélité | 🔄 Post-MVP |
| Portail client | Accès client à son historique | 🔄 Post-MVP |

---

## Liens rapides

- [Architecture technique](architecture/stack.md)
- [Infrastructure serveur](architecture/server.md)
- [Schéma base de données](architecture/database.md)
- [Logique import & fusion](architecture/data-merge.md)
- [Setup développement local (VMware)](dev/getting-started.md)
- [Workflow Git & déploiement](dev/git-workflow.md)
- [Migration vers nouveau serveur](deploy/migration.md)
- [Guide utilisateur Allyson](user/guide-allyson.md)
