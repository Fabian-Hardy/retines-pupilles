# IDEAS.md — Rétines & Pupilles

> Idées capturées pendant les sessions. Géré par opt-end.
> Format : idée brève + contexte + priorité estimée.
> Ne pas supprimer — archiver dans la section "Rejetées/Reportées" si non retenu.

---

## 💡 Idées actives (à évaluer)

### IDEA-001 — Stock temps réel
**Contexte :** Allyson a dit que l'inventaire est annuel aujourd'hui, mais avoir le stock en temps réel serait un plus.
**Ce que ça implique :** Modèle `Article` avec champ `quantite_stock`, mouvement à chaque commande. Pas bloquant pour MVP mais le modèle de données doit le prévoir dès Sprint 1.
**Priorité estimée :** Phase 2 (après noyau MVP)
**Action :** Inclure `quantite_stock: int | None` dans le modèle Article dès TASK-003, même si l'UI n'expose pas encore cette fonctionnalité.

### IDEA-002 — Champ `site` sur les entités
**Contexte :** Allyson travaille rarement à Welkenraedt. Multi-magasin marqué "Utile" mais pas urgent.
**Ce que ça implique :** Ajouter `site: str | None` (défaut "heusy") sur Client et Prescription. Migration facile à faire maintenant, pénible à retrofitter plus tard.
**Priorité estimée :** Ajouter le champ en DB dès Sprint 1, UI ignorée jusqu'en Phase 3.
**Action :** Intégrer dans TASK-003 comme champ nullable.

### IDEA-003 — Détection de doublons avec suggestion (pas auto-merge)
**Contexte :** Allyson préfère garder deux fiches. Mais une alerte "ce client ressemble à X" serait utile.
**Ce que ça implique :** Fuzzy match sur (nom + prénom + date naissance) à la création. Badge jaune d'avertissement, pas de blocage.
**Priorité estimée :** Phase 2
**Libs :** rapidfuzz (déjà dans le stack)

### IDEA-004 — Export PDF pour mutuelle
**Contexte :** Allyson prépare les documents mutuelle pour le client (elle n'envoie pas directement).
**Ce que ça implique :** Template PDF pré-rempli (nom, prénom, montant, date, prescription). Le client emporte la feuille.
**Priorité estimée :** Phase 2
**Libs :** reportlab ou weasyprint

### IDEA-005 — Rappels renouvellement prescription
**Contexte :** Marqué "Utile" par Allyson. Rappeler qu'une prescription expire (généralement 3 ans pour adultes).
**Ce que ça implique :** Champ `date_expiration` sur Prescription + job cron quotidien.
**Priorité estimée :** Phase 3

---

## 📦 Idées reportées (Phase 4+)

- **Statistiques** (clients, ventes, produits populaires) — utile mais pas urgent
- **Export Excel/CSV** — utile pour comptable, Phase 3
- **Intégration comptable** — fichiers pour comptable, Phase 4
- **Multi-utilisateurs avec droits** — si Allyson a des assistants un jour

---

## ❌ Idées rejetées

*(vide pour l'instant)*
