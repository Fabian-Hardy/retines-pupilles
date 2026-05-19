# Réponses d'Allyson — Questionnaire Rétines & Pupilles

> Réponses collectées en mai 2026. Source : 15 captures d'écran du questionnaire Word complété sur mobile.
> Ce document est la référence métier pour toutes les décisions de conception.

---

## Section A — Journée type

| Question | Réponse |
|---|---|
| A1. Clients par jour | **5-10 clients** |
| A2. Flux par client (étapes) | *Non rempli — à clarifier* |
| A3. 3 tâches admin les plus chronophages | *Non rempli — à clarifier* |
| A4. Consultation historique avant visite | **Systématiquement (avant chaque client)** |
| A5. Accès hors magasin (maison, phone) | **Rarement (une fois par mois)** |

**Implications pour le dev :**
- Volume modéré (5-10/jour) → pas besoin d'optimisation extrême pour la concurrence
- Historique consulté **avant chaque client** → la recherche client doit être rapide, max 2-3 clics depuis l'accueil
- Accès mobile rare → l'interface mobile est "nice to have", pas bloquante pour le MVP

---

## Section B — Informations client

### B1. Champs indispensables
✅ Nom, prénom
✅ Date de naissance
✅ Téléphone mobile (GSM)
❌ Adresse complète (pas indispensable)
❌ Téléphone fixe (pas indispensable)
❌ Email (pas indispensable)
❌ Profession / Métier (pas indispensable)
❌ Mutuelle (pas indispensable)
❌ Notes / Remarques (pas indispensable)

### B2. Contact après visite
**Par tous les moyens (dépend du client)** — SMS, email, téléphone selon la préférence du client

### B3. Gestion des doublons
**Garder les deux fiches** — pas de fusion automatique, Allyson décide manuellement

**Implications pour le dev :**
- Modèle client minimal : `nom`, `prénom`, `date_naissance`, `gsm` sont les 4 champs REQUIRED
- Adresse, email, mutuelle → optionnels (peuvent venir de l'import EDOPT)
- Pas de déduplication automatique → l'interface peut signaler les doublons potentiels mais ne fusionne jamais sans validation
- Multi-canal contact → champ `preference_contact` à prévoir

---

## Section C — Ordonnances et verres

| Question | Réponse |
|---|---|
| C1. Conservation prescriptions | **Toutes les prescriptions** (pas de purge) |
| C2. Paires de verres / client / an | **Moins d'une paire** |
| C3. Tracker montages en cours | **Non, pas nécessaire** |
| C4. Lentilles de contact | **Oui, sur commande (prescription spécialisée)** |

**Implications pour le dev :**
- Historique de prescriptions complet — pas de limite, pas de purge automatique
- Volume faible de commandes verres → pas besoin de workflow complexe de suivi de production
- Pas de tracking de statut de montage (en cours / reçu / livré) pour le MVP
- Lentilles sur commande : gérer comme un article de catalogue spécial, pas du stock permanent

---

## Section D — Documents & Mutuelles

| Question | Réponse |
|---|---|
| D1. Documents émis | **Factures ET reçus** (les deux) |
| D2. Remises / codes promo | **Oui, remises ponctuelles** (promotions, fidélité) |
| D3. Remboursements mutuelles | **Oui — prépare les documents pour le client** (elle n'envoie pas directement) |
| D4. Appareils auditifs / autres produits | **Non** — optique uniquement |
| D5. Inventaire | **Une fois par an** |

**Implications pour le dev :**
- Deux types de documents : facture (avec TVA, n° client) + reçu (justificatif simple)
- Système de remises : montant fixe ou % sur ligne / commande, sans règle récurrente complexe
- Module mutuelle : générer le document type (attestation, formulaire) que le client emporte — pas d'envoi électronique direct
- Scope = optique uniquement, pas d'extension audiologie prévue
- Inventaire annuel → pas de tracking temps réel nécessaire, mais export du stock à date

---

## Tableau de priorités — 16 fonctionnalités

Légende : **I** = Indispensable (je ne peux pas m'en passer) | **U** = Utile (ça m'aiderait)

| # | Fonctionnalité | I | U |
|---|---|---|---|
| 1 | Gestion clients (création, modification, historique) | ✅ | |
| 2 | Recherche client rapide (nom, GSM, adresse) | ✅ | |
| 3 | Enregistrement des prescriptions (visionnelle) | ✅ | |
| 4 | Stock & gestion de fournisseurs | ✅ | |
| 5 | Commandes de verres/montures | ✅ | |
| 6 | Suivi d'une commande (en cours, reçu, livré) | | ✅ |
| 7 | Facturation & documents commerciaux | ✅ | |
| 8 | Gestion des mutuelles & remboursements | | ✅ |
| 9 | Rappels (renouvellement ordonnance, délai verres) | | ✅ |
| 10 | Statistiques (clients, ventes, produits populaires) | | ✅ |
| 11 | Export de données (Excel, CSV, PDF) | | ✅ |
| 12 | Accès web/mobile (consulting depuis la maison) | | ✅ |
| 13 | Synchronisation multi-magasin (Heusy + Welkenraedt) | | ✅ |
| 14 | Intégration comptable (fichiers pour comptable) | | ✅ |
| 15 | Gestion des droits d'accès (plusieurs utilisateurs) | | ✅ |
| 16 | Sauvegarde automatique / archivage | | ✅ |

### Lecture du tableau

**MVP obligatoire (6 fonctionnalités I) :**
Clients → Recherche → Prescriptions → Stock/Fournisseurs → Commandes → Facturation

**Post-MVP priorité haute (Utile mais signalés en priorité) :**
Mutuelles, Rappels, Export données, Accès web/mobile

**Futur / v2 (Utile, moins urgent) :**
Statistiques, Synchro multi-magasin, Comptabilité, Multi-utilisateurs, Sauvegarde

---

## Points d'attention notables

### 🔴 Multi-magasin (Heusy + Welkenraedt)
Allyson a coché "Utile" pour la synchronisation multi-magasin. Cela implique qu'elle travaille ou a travaillé dans les deux magasins. À clarifier :
- Est-elle régulièrement à Welkenraedt ?
- Veut-elle partager les fiches clients entre les deux sites ?
- Ou juste exporter/importer ponctuellement ?

### 🟡 Tâches chronophages non renseignées (A3)
Les 3 tâches administratives les plus chronophages n'ont pas été remplies. Ce sont pourtant les cibles directes du gain de temps. À relancer Allyson sur ce point.

### 🟡 Flux client non renseigné (A2)
Le flux détaillé d'une visite client n'a pas été décrit. Important pour modéliser le workflow de l'interface.

### ✅ Scope bien délimité
- Pas d'auditifs → scope optique pur
- Inventaire annuel → pas de complication de stock temps réel
- Accès mobile rare → responsive utile mais pas critique
