# Logs backend

Le backend FastAPI utilise des logs structures avec la bibliotheque standard Python.
Le format par defaut est JSON, configurable avec `LOG_FORMAT=json`.
`LOG_FORMAT=text` reste disponible pour le developpement local.

## Format JSON

Chaque ligne JSON contient au minimum :

| Champ | Description |
|---|---|
| `timestamp` | Horodatage UTC ISO 8601 |
| `level` | Niveau Python (`INFO`, `WARNING`, `ERROR`, etc.) |
| `logger` | Nom du logger |
| `message` | Nom court de l'evenement |

Les logs applicatifs peuvent ajouter uniquement des champs explicitement autorises :

| Champ | Usage |
|---|---|
| `event` | Nom machine de l'evenement |
| `app_env`, `app_version`, `app_domain` | Contexte de demarrage |
| `http_method`, `http_path`, `status_code`, `duration_ms` | Requetes HTTP |

Exemple :

```json
{"duration_ms":12.3,"event":"http_request","http_method":"GET","http_path":"/api/v1/health","level":"INFO","logger":"retines.app.main","message":"http_request","status_code":200,"timestamp":"2026-06-12T08:30:00Z"}
```

## Politique de confidentialite

Les logs ne doivent pas contenir de donnees patient, secrets ou details internes.

- Ne pas logger les corps de requete ou de reponse.
- Ne pas logger les query strings, car elles peuvent contenir des recherches patient.
- Ne pas logger les headers, cookies, sessions, JWT ou tokens `Authorization`.
- Ne pas logger les mots de passe, `hashed_password`, cles secretes ou chaines de connexion.
- Ne pas logger les exceptions brutes, traces d'appel ou details internes d'erreur.

Le formateur redacte les motifs secrets courants (`password=...`, `token=...`, `Bearer ...`),
mais cette protection est un filet de securite. La regle principale reste de ne jamais
passer de donnees sensibles au logger.

## Configuration

`LOG_LEVEL` conserve le comportement existant : les valeurs Python usuelles sont acceptees,
et une valeur invalide retombe sur `INFO`.

```bash
LOG_LEVEL=INFO
LOG_FORMAT=json
```
