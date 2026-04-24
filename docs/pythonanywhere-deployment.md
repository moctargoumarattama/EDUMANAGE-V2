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

## 2 bis. Workflow recommande pour le pack audio vocabulaire

Pour un site deja en ligne sur PythonAnywhere, le plus fiable est:

1. generer les `.wav` en local
2. uploader les fichiers sous `media/uploads/audios/vocab_pack/`
3. appliquer le manifeste CSV sur la base PythonAnywhere

### Generation locale

Depuis le dossier du projet local :

```bash
.\.venv\Scripts\python.exe scripts\generate_vocab_audio_pack.py ^
  --piper-binary "C:\chemin\vers\piper.exe" ^
  --piper-model "C:\chemin\vers\ar_JO-kareem-medium.onnx" ^
  --manifest-path "instance\exports\vocab_audio_manifest.csv"
```

Options utiles :

- ajoutez `--write-db` si vous voulez aussi remplir `audio_url` dans votre base locale
- ajoutez `--overwrite-files` pour regenerer les `.wav` deja presents
- ajoutez `--overwrite-existing-audio` seulement si vous voulez remplacer des `audio_url` deja renseignes

### Upload vers PythonAnywhere

Copiez le contenu local :

```text
media/uploads/audios/vocab_pack/
```

vers le dossier PythonAnywhere :

```text
/home/<votre-utilisateur>/EDUMANAGE/media/uploads/audios/vocab_pack/
```

Vous pouvez faire cela via l'onglet `Files`, `scp`, `rsync` ou votre methode habituelle de deploiement.

### Bundle zip optionnel

Si vous preferez preparer un seul fichier a envoyer, vous pouvez creer un bundle :

```bash
.\.venv\Scripts\python.exe scripts\package_vocab_audio_bundle.py
```

Cela produit par defaut :

```text
instance/exports/vocab_audio_bundle.zip
```

Le zip contient :

- `media/uploads/audios/vocab_pack/...`
- `instance/exports/vocab_audio_manifest.csv`

Une fois le zip envoye sur PythonAnywhere, dezippez-le a la racine du projet `EDUMANAGE`.

### Application du manifeste sur PythonAnywhere

Copiez aussi le manifeste :

```text
instance/exports/vocab_audio_manifest.csv
```

sur le serveur, puis lancez :

```bash
cd /home/<votre-utilisateur>/EDUMANAGE
source /home/<votre-utilisateur>/.virtualenvs/edumanage-env/bin/activate
python scripts/apply_vocab_audio_manifest.py --manifest-path instance/exports/vocab_audio_manifest.csv
```

Par defaut, ce script ne remplace pas les `audio_url` deja renseignes. Pour forcer le remplacement :

```bash
python scripts/apply_vocab_audio_manifest.py --manifest-path instance/exports/vocab_audio_manifest.csv --overwrite-existing-audio
```

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
- ouvrez un mot pedagogique connu dans le popup dico pour verifier qu'il retourne maintenant un vrai `audio_url`
- testez directement une URL comme `/media/uploads/audios/vocab_pack/<fichier>.wav`

## 7. Notes utiles

- Les anciens fichiers `app/static/uploads/` sont recopies automatiquement vers `media/uploads/` au demarrage.
- Les URLs stockees en base restent en `uploads/...`, mais sont maintenant servies sous `/media/uploads/...`.
- Les logs applicatifs sont ecrits dans `logs/platform.log`.
- Si vous deployez par `git`, attention: `instance/` et `media/uploads/audios/` sont ignores par le repo. Les `.wav` generes localement et le manifeste CSV doivent donc etre envoyes separement a la production.
