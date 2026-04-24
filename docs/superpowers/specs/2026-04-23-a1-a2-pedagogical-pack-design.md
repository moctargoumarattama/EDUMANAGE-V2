# A1 A2 Pedagogical Pack Design

**Goal**

Remplir localement le projet avec un vrai pack pedagogique arabe debutant, stable et idempotent, compose de 1000 entrees de vocabulaire, 2 parcours publies, 20 lecons publiees et un placement leger limite a 10 questions.

**Scope**

- 1000 entrees pedagogiques locales
- 500 entrees `A1`
- 500 entrees `A2`
- 2 parcours publies par defaut
- 10 lecons par parcours
- 50 entrees de vocabulaire par lecon
- 4 exercices faciles minimum par lecon
- 10 questions de placement au total
- priorite aux vraies lecons et aux vrais cours

**Contraintes produit**

- vocabulaire utile, frequent et simple a reutiliser
- progression douce, avec themes concrets avant les phrases plus fonctionnelles
- exemples courts et naturels
- compatibilite stricte avec les modeles SQLAlchemy existants
- pas de changement de schema
- audio manuel optionnel seulement
- si aucun audio manuel n'est fourni, reutiliser le systeme existant de resolution/generation audio
- seed idempotent autant que possible
- cours et lecons publies par defaut

**Architecture**

- Ajouter un module dedie `app/pedagogical_seed.py`.
- Garder `_bootstrap_runtime_data()` comme point d'entree global du seed local.
- Deplacer le contenu pedagogique dans des specs Python locales plutot que dans `app/__init__.py`.
- Generer automatiquement:
  - la translitteration de base
  - le contenu HTML des lecons
  - les exemples courts
  - les 4 exercices minimum par lecon
  - les 10 questions de placement leger

**Structure pedagogique**

- Parcours 1:
  - `A1`
  - bases utiles du quotidien
  - 10 lecons thematiques de 50 entrees
- Parcours 2:
  - `A2`
  - quotidien elargi, autonomie simple, situations frequentes
  - 10 lecons thematiques de 50 entrees

**Modele de seed**

- `Vocabulaire`
  - upsert par `mot_arabe`
  - renseigner `translitteration`, `traduction_fr`, `exemple_phrase`, `niveau_cefr`, `theme`, `est_pedagogique`
  - laisser `audio_url` vide par defaut pour activer le systeme existant
- `Cours`
  - 2 enregistrements publies
  - rattaches au compte enseignant demo s'il existe
- `Lecon`
  - 10 lecons par cours
  - `est_publie=True`
  - `date_publication` renseignee
- `Question`
  - 4 questions minimum par lecon
  - types limites aux types deja geres par le projet: `qcm`, `ecoute`, `ordre_mots`, `dictee`
- `PlacementQuestion`
  - 10 questions total
  - 5 derivees de contenus `A1`
  - 5 derivees de contenus `A2`

**Idempotence**

- vocabulaire mis a jour si l'entree existe deja
- cours identifies par nom seed ou ancien nom de demo connu
- lecons synchronisees par ordre dans chaque cours seed
- questions synchronisees par ordre dans chaque lecon
- choix synchronises par position
- anciennes demos connues recyclees ou nettoyees sans toucher aux contenus utilisateur hors seed

**Compatibilite**

- aucun nouveau champ en base
- aucun changement attendu dans les vues ou blueprints existants
- les exercices utilisent les types deja serialises par `app/utils.py`
- l'audio s'appuie sur `app/audio.py`
- le placement reste compatible avec `MAX_PLACEMENT_QUESTION_COUNT = 10`

**Tests attendus**

- le seed produit exactement 1000 entrees pedagogiques
- la repartition `A1/A2` est exactement `500/500`
- 2 cours publies seed existent
- chaque cours seed contient 10 lecons publiees
- chaque lecon seed contient au moins 4 questions
- le placement seed contient exactement 10 questions
- la repartition logique du placement est `5 A1 + 5 A2`
- le seed est idempotent quand on le relance
