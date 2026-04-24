# Piper Vocab Audio Pack Design

**Goal**

Ajouter un flux fiable de pre-generation audio locale pour les mots arabes du pack pedagogique, puis appliquer ces chemins audio en production sans dependre de Piper ni de la voix du navigateur sur PythonAnywhere.

**Scope**

- generation locale des `.wav` Piper pour le vocabulaire arabe cible
- nommage stable des fichiers audio
- export d'un manifeste de mise a jour `mot_arabe -> audio_url`
- application sure des `audio_url` en base sans ecraser les audios deja presents
- documentation operateur pour local -> PythonAnywhere

**Contraintes produit**

- aucun changement de schema
- ne pas ecraser les `audio_url` deja renseignes par un vrai fichier manuel
- fichiers de sortie servis sous `uploads/audios/vocab_pack/...`
- comportement idempotent si on relance la generation
- la prod PythonAnywhere ne doit pas avoir besoin de Piper pour lire les audios

**Architecture**

- Ajouter un module dedie `app/vocab_audio_pack.py`.
- Garder `app/audio.py` comme couche de resolution/lecture cote application.
- Ajouter un script local de generation qui utilise Piper via la configuration Flask ou des arguments CLI.
- Ajouter un script distinct pour appliquer le manifeste en base sur l'environnement cible.

**Flux**

1. Le script local charge l'application Flask et cible les entrees `Vocabulaire` pedagogiques sans `audio_url`.
2. Pour chaque mot arabe, il calcule un chemin stable sous `uploads/audios/vocab_pack/`.
3. Il genere un `.wav` via Piper uniquement si le fichier n'existe pas deja, sauf si on force l'ecrasement.
4. Il exporte un CSV manifeste avec `mot_arabe` et `audio_url`.
5. Un second script applique ce manifeste sur la base locale ou PythonAnywhere, sans remplacer les `audio_url` existants sauf si on le demande explicitement.
6. Une fois les fichiers uploades sous `media/uploads/audios/vocab_pack/` et le manifeste applique, l'UI recoit naturellement `audio_mode = file`.

**Compatibilite**

- `app/audio.py` continue a preferer `audio_url` manuel/fichier
- le fallback navigateur reste disponible pour les mots non encore pre-generes
- aucun impact attendu sur les lecons, le quiz, ni le placement

**Tests attendus**

- un mot pedagogique arabe sans audio recoit un fichier stable et une ligne de manifeste
- un mot avec `audio_url` existant n'est pas ecrase par defaut
- l'application du manifeste remplit les `audio_url` vides sans remplacer les existants
- la generation est relancable sans duplication ni nommage instable
