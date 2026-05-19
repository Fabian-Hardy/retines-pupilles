# Import DBF et fusion intelligente

## Contexte

La base de données principale du magasin ED Optique tourne sous EDOPT (MS-DOS, années 1990) et stocke ses données en fichiers dBASE III/IV (.DBF). Rétines & Pupilles peut importer ces fichiers pour démarrer avec les données existantes et se mettre à jour périodiquement.

**Fichiers source EDOPT :**

| Fichier | Contenu | Volume |
|---|---|---|
| `ADMINIST.DBF` | Clients | ~20 710 enregistrements |
| `PRESCRIP.DBF` | Prescriptions optométriques | ~68 298 enregistrements |
| `INVENT.DBF` | Stock (montures, verres) | ~5 602 articles |
| `FOURNIS.DBF` | Fournisseurs | 143 entrées |
| `LENTILLE.DBF` | Clients lentilles de contact | 18 dossiers |
| `MEMO.DBF` | Notes clients | 68 entrées |

---

## Modèle de données pour la fusion

Chaque enregistrement dans Rétines & Pupilles porte deux métadonnées critiques :

```python
class Client(Base):
    # ... champs métier ...

    # Métadonnées de fusion
    source: str          # "main_db" | "allyson"
    external_id: str     # ID original dans la DB principale (NUMCLIENT EDOPT)
    allyson_modified_fields: list[str]  # champs modifiés par Allyson
    last_import_hash: str  # hash de la dernière version importée de cet enregistrement
    created_at: datetime
    updated_at: datetime
```

- `source = "main_db"` : enregistrement venu d'un import EDOPT
- `source = "allyson"` : enregistrement créé directement par Allyson dans l'app
- `allyson_modified_fields` : liste des champs qu'Allyson a modifiés sur un enregistrement `main_db`

---

## Logique de fusion — 4 cas

```
Import d'un nouvel fichier DBF
         │
         ▼
Pour chaque enregistrement du fichier entrant :
         │
         ├── Absent de la DB locale ?
         │         └── → AJOUTER (source="main_db")
         │
         ├── Présent, source="allyson" ?
         │         └── → IGNORER (jamais écrasé)
         │
         ├── Présent, source="main_db", aucun champ modifié par Allyson ?
         │         └── → REMPLACER intégralement
         │
         └── Présent, source="main_db", certains champs modifiés par Allyson ?
                   └── → FUSIONNER champ par champ :
                         - Champs dans allyson_modified_fields → garder valeur Allyson
                         - Autres champs → prendre valeur du nouveau fichier
                         - Si conflit détecté → mettre en file "conflits à résoudre"
```

### Détection des changements

Pour savoir ce qui a changé entre l'ancienne et la nouvelle version de la DB principale, on compare le `last_import_hash` de chaque enregistrement avec le hash de la même entrée dans le nouveau fichier. Si identiques → pas de changement → skip.

---

## Résumé post-import

Après chaque import, l'interface affiche un résumé clair :

```
Import terminé — 15 mai 2026, 14h32

  ✅ 32 nouveaux clients ajoutés
  🔄 8 enregistrements mis à jour
  🛡️  145 enregistrements ignorés (données Allyson protégées)
  ⚠️  3 conflits à résoudre manuellement

[Voir les conflits →]
```

Pour les conflits, Allyson voit côte à côte :
- La valeur qu'elle a entrée
- La nouvelle valeur reçue de la DB principale
- Un bouton "Garder le mien" / "Prendre la mise à jour"

---

## Anomalies EDOPT à gérer lors de l'import

Ces anomalies ont été identifiées lors de l'audit des fichiers dBASE :

| Anomalie | Description | Traitement |
|---|---|---|
| Dates incohérentes | 3 formats différents (YYYY/MM/DD, DD/MM/YYYY, YY/MM/DD), dates aberrantes (1900-00-00, 2050-12-31) | Normalisation en ISO 8601, dates invalides → `null` avec flag |
| Francs belges (BEF) | Prix avant 2002 en BEF (taux : 40.3399 BEF = 1 EUR) | Stocker BEF d'origine + champ EUR converti |
| Mutuelle texte libre | "MUTUALIA", "Mutualia", "MUTUEL ALIA" = même chose | Normalisation par matching fuzzy vers liste fermée |
| SEXE inversé | O = féminin, N = masculin (convention EDOPT) | Inverser à l'import |
| PROFESSION contient GSM | Champ mal utilisé dans l'ancien système | Détecter pattern téléphone → déplacer vers champ GSM |
| Codes stock obscurs | TYPE, MATIÈRE, ÉCART = codes 1 caractère non documentés | Importer tel quel, table de référence à compléter avec Allyson |
| Factures sans NUMCLIENT | Pas de lien direct facture → client dans EDOPT | Factures historiques laissées en archive EDOPT, pas migrées |

---

## Service Python — implémentation

```python
# backend/app/services/import_service.py

class DBFImportService:

    async def import_file(self, file_path: str) -> ImportResult:
        records = self._read_dbf(file_path)
        result = ImportResult()

        for record in records:
            normalized = self._normalize(record)
            existing = await self._find_existing(normalized.external_id)

            if existing is None:
                await self._create(normalized)
                result.added += 1

            elif existing.source == "allyson":
                result.skipped += 1  # jamais touché

            elif not existing.allyson_modified_fields:
                await self._update_full(existing, normalized)
                result.updated += 1

            else:
                merged, conflicts = self._merge(existing, normalized)
                await self._save(merged)
                result.conflicts.extend(conflicts)

        return result

    def _normalize(self, record) -> NormalizedRecord:
        # Corrections dates, BEF→EUR, mutuelle, sexe, profession/GSM
        ...

    def _merge(self, existing, incoming) -> tuple[Record, list[Conflict]]:
        # Fusion champ par champ selon allyson_modified_fields
        ...
```

---

## Bibliothèques Python utilisées

| Lib | Usage |
|---|---|
| `dbfread` | Lecture fichiers .DBF (dBASE III/IV) |
| `chardet` | Détection encodage (les fichiers EDOPT sont en CP850/Latin-1) |
| `rapidfuzz` | Fuzzy matching pour normalisation des mutuelles |
| `pydantic` | Validation et normalisation des données importées |
