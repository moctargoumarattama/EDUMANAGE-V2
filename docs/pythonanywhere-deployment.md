# Deploiement PythonAnywhere

## 1. Creer le virtualenv

```bash
mkvirtualenv --python=/usr/bin/python3.11 edumanage-env
pip install -r /home/<votre-utilisateur>/EDUMANAGE/requirements.txt
```

## 2. Variables d'environnement

Dans l'onglet `Web` ou dans le fichier de virtualenv, configurez au minimum :

```bash
export SECRET_KEY="remplace-moi"
export SECURITY_PASSWORD_SALT="remplace-moi-aussi"
export DATABASE_URL="sqlite:////home/<votre-utilisateur>/EDUMANAGE/instance/ecole.db"
export MEDIA_ROOT="/home/<votre-utilisateur>/EDUMANAGE/media"
export MEDIA_URL="/media"
export SESSION_COOKIE_SECURE="1"
export PREFERRED_URL_SCHEME="https"
```

Variables optionnelles :

```bash
export GOOGLE_OAUTH_CLIENT_ID=""
export GOOGLE_OAUTH_CLIENT_SECRET=""
export PIPER_BINARY=""
export PIPER_MODEL=""
export PIPER_CONFIG=""
export PIPER_SPEAKER=""
export VAPID_PRIVATE_KEY="/home/<votre-utilisateur>/EDUMANAGE/vapid_private.pem"
export VAPID_PUBLIC_KEY=""
export VAPID_SUBJECT="mailto:admin@votre-domaine.com"
```

Si `PIPER_BINARY` ou `PIPER_MODEL` est vide, l'application demarre quand meme et utilise les audios deja presents.

## 3. WSGI

Dans le fichier WSGI PythonAnywhere :

```python
import sys

project_home = "/home/<votre-utilisateur>/EDUMANAGE"
if project_home not in sys.path:
    sys.path.insert(0, project_home)

from pythonanywhere_wsgi import application
```

Le projet fournit deja `pythonanywhere_wsgi.py` avec :

```python
from app import create_app

app = create_app()
application = app
```

## 4. Static mappings

Ajoutez ces mappings dans l'onglet `Web` :

- URL `/static/` -> dossier `/home/<votre-utilisateur>/EDUMANAGE/app/static/`
- URL `/media/` -> dossier `/home/<votre-utilisateur>/EDUMANAGE/media/`

## 5. Base SQLite

La configuration par defaut pointe maintenant vers :

```text
instance/ecole.db
```

Si vous laissez `DATABASE_URL` vide, Flask utilisera automatiquement ce fichier.

## 6. Verification rapide

Apres reload de la web app :

- ouvrez `/health`
- verifiez que la reponse contient `{"status":"ok","database":"ok"}`
- ouvrez une lecon avec audio pour verifier `/media/uploads/...`

## 7. Notes utiles

- Les anciens fichiers `app/static/uploads/` sont recopies automatiquement vers `media/uploads/` au demarrage.
- Les URLs stockees en base restent en `uploads/...`, mais sont maintenant servies sous `/media/uploads/...`.
- Les logs applicatifs sont ecrits dans `logs/platform.log`.
