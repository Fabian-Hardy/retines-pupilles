# Guide utilisateur — Allyson

## Bienvenue dans Rétines & Pupilles

Rétines & Pupilles est ton outil de gestion personnel pour le magasin. Il te permet de gérer tes clients, leurs prescriptions et tes commandes depuis n'importe quel appareil avec un navigateur — ordinateur, tablette, téléphone.

**L'application est accessible à l'adresse : `https://app.[DOMAIN]`**

---

## Connexion

1. Ouvrir `https://app.[DOMAIN]` dans ton navigateur
2. Entrer ton identifiant et mot de passe
3. Tu restes connectée pendant 7 jours sans devoir te reconnecter

> Si tu oublies ton mot de passe, contacter Fabian pour le réinitialiser.

---

## Tes clients

### Chercher un client

La barre de recherche en haut de la page Clients permet de chercher par :
- Nom ou prénom
- Numéro de téléphone
- Adresse

### Créer un nouveau client

1. Cliquer **"Nouveau client"**
2. Remplir les informations (seul le nom est obligatoire)
3. **Enregistrer**

Le client est marqué comme *"créé par toi"* — il ne sera jamais écrasé lors des mises à jour de la base de données du magasin.

### Modifier un client existant

1. Ouvrir la fiche du client
2. Cliquer **"Modifier"**
3. Changer les champs souhaités
4. **Enregistrer**

Les champs que tu modifies sont mémorisés. Lors de la prochaine mise à jour de la DB du magasin, tes modifications seront conservées même si le magasin a modifié ce client de son côté.

---

## Les prescriptions

### Consulter l'historique

Dans la fiche d'un client, l'onglet **"Prescriptions"** affiche toutes ses ordonnances, de la plus récente à la plus ancienne.

### Saisir une nouvelle prescription

1. Ouvrir la fiche du client
2. Cliquer **"Nouvelle prescription"**
3. Remplir les données optométriques :
   - **OD** (œil droit) : sphère, cylindre, axe
   - **OG** (œil gauche) : sphère, cylindre, axe
   - Addition (si progressive)
   - Écart pupillaire (EP)
   - Date de la mesure
4. **Enregistrer**

---

## Les commandes

### Créer une commande

1. Ouvrir la fiche du client
2. Aller dans l'onglet **"Commandes"**
3. Cliquer **"Nouvelle commande"**
4. Sélectionner la prescription associée
5. Choisir les verres et la monture
6. **Enregistrer**

### Suivre une commande

Chaque commande affiche son état :
- 🟡 **En attente** — commande créée, pas encore envoyée
- 🔵 **Commandée** — envoyée au fournisseur
- 🟠 **Reçue** — arrivée en magasin, pas encore remise au client
- ✅ **Livrée** — remise au client

Cliquer sur l'état pour le mettre à jour.

---

## Mettre à jour depuis la base de données du magasin

Quand tu reçois un nouveau fichier de la base de données du magasin (par exemple par email ou clé USB) :

1. Aller dans **Paramètres → Import de données**
2. Cliquer **"Importer un fichier"**
3. Sélectionner le fichier reçu (format `.dbf` ou `.zip`)
4. L'application analyse le fichier et affiche un aperçu :
   - Nombre de nouveaux clients à ajouter
   - Nombre de fiches à mettre à jour
   - Tes données personnelles qui seront protégées
5. Si tout semble correct, cliquer **"Confirmer l'import"**

### Si des conflits sont détectés

Parfois, toi et le magasin avez modifié la même information sur un client. L'application te montre les conflits et te laisse choisir :

- **"Garder ma version"** — conserver ce que tu as saisi
- **"Prendre la mise à jour"** — utiliser la nouvelle valeur du magasin

---

## Conseils pratiques

**Accès mobile** — L'application fonctionne sur téléphone. Ajoute-la à l'écran d'accueil de ton iPhone/Android pour un accès rapide.

**Sauvegarde** — Tes données sont sauvegardées automatiquement chaque nuit. Tu ne peux pas les perdre.

**Données protégées** — Tout ce que tu saisis toi-même (nouveaux clients, modifications, notes) ne sera jamais écrasé lors des mises à jour de la DB du magasin.
