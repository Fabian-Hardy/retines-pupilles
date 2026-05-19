# Variables d'environnement

## Règles

- **Jamais** de secrets dans Git (`.env.*` sont dans `.gitignore`)
- **`.env.example`** est committé avec toutes les variables et des valeurs fictives
- En dev : `.env.dev` dans la VM
- En prod : `.env.prod` sur le serveur à `/srv/retines-pupilles/.env.prod`

---

## `.env.example` — toutes les variables

```bash
# ─────────────────────────────────────────────
# APPLICATION
# ─────────────────────────────────────────────
APP_ENV=development           # development | production
APP_SECRET_KEY=change_me_32_chars_minimum
APP_VERSION=0.1.0
APP_DOMAIN=app.retinespupilles.be

# ─────────────────────────────────────────────
# BASE DE DONNÉES
# ─────────────────────────────────────────────
DB_HOST=postgresql            # nom du service Docker
DB_PORT=5432
DB_NAME=retines_db
DB_USER=retines
DB_PASS=change_me_db_password
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# ─────────────────────────────────────────────
# REDIS
# ─────────────────────────────────────────────
REDIS_HOST=redis              # nom du service Docker
REDIS_PORT=6379

# ─────────────────────────────────────────────
# AUTHENTIFICATION JWT
# ─────────────────────────────────────────────
JWT_SECRET_KEY=change_me_jwt_secret_64_chars_min
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
JWT_ALGORITHM=HS256

# ─────────────────────────────────────────────
# OLLAMA (IA locale)
# ─────────────────────────────────────────────
OLLAMA_HOST=ollama            # nom du service Docker
OLLAMA_PORT=11434
OLLAMA_MODEL=llama3.2:3b
OLLAMA_ENABLED=false          # false en MVP, true quand activé

# ─────────────────────────────────────────────
# STOCKAGE FICHIERS (imports DBF, exports PDF)
# ─────────────────────────────────────────────
STORAGE_PATH=/app/storage     # chemin dans le container

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
LOG_LEVEL=INFO                # DEBUG | INFO | WARNING | ERROR
LOG_FORMAT=json               # json (prod) | text (dev)
```

---

## Valeurs spécifiques par environnement

### Dev (`.env.dev`)

```bash
APP_ENV=development
APP_SECRET_KEY=dev_secret_not_for_prod_32chars
LOG_LEVEL=DEBUG
LOG_FORMAT=text
OLLAMA_ENABLED=false
DB_PASS=dev_password_local
JWT_SECRET_KEY=dev_jwt_secret_not_for_prod
```

### Prod (`.env.prod` — sur le serveur uniquement)

```bash
APP_ENV=production
APP_SECRET_KEY=[généré avec: python -c "import secrets; print(secrets.token_hex(32))"]
LOG_LEVEL=INFO
LOG_FORMAT=json
OLLAMA_ENABLED=false   # passer à true quand fonctionnalité IA activée
DB_PASS=[mot de passe fort, généré aléatoirement]
JWT_SECRET_KEY=[généré avec: python -c "import secrets; print(secrets.token_hex(64))"]
```

---

## Générer des secrets sécurisés

```bash
# Secret applicatif (32 bytes hex = 64 chars)
python3 -c "import secrets; print(secrets.token_hex(32))"

# Secret JWT (64 bytes hex = 128 chars)
python3 -c "import secrets; print(secrets.token_hex(64))"

# Mot de passe DB (alphanumérique, 24 chars)
python3 -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(24)))"
```

---

## Accès aux variables dans le code

```python
# backend/app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_env: str = "development"
    app_secret_key: str
    db_host: str = "postgresql"
    db_port: int = 5432
    db_name: str = "retines_db"
    db_user: str = "retines"
    db_pass: str
    jwt_secret_key: str
    jwt_access_token_expire_minutes: int = 15
    # ...

    class Config:
        env_file = ".env.dev"  # override via ENV variable en prod

settings = Settings()
```

Toutes les variables sont **typées et validées au démarrage**. Si une variable obligatoire manque, l'application refuse de démarrer avec un message d'erreur clair.
