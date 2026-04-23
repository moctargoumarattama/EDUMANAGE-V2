# Premium Loader Jewel Reveal V4.0

## Contexte

L'application LabeeB Arabic dispose deja d'un shell de navigation avec une barre de progression, un loader de page discret et des evenements partages `app:navigation-start` et `app:navigation-stop`.

Le besoin est d'elever nettement la perception premium sur mobile iPhone et Android avec :

- un splash plein ecran anime au tout premier chargement ;
- une version plus courte pendant les changements de page ;
- une direction visuelle "Luxe dore" ;
- un rendu rapide, fluide et fiable en conditions reseau normales.

Le fichier `moctar` ne fait pas partie du scope.

## Objectif

Creer un systeme de chargement "Jewel Reveal" version 4.0 qui donne une premiere impression haut de gamme sans ralentir l'application ni ajouter de dependances lourdes.

Le resultat doit :

- afficher le logo LabeeB au centre dans un ecrin premium ;
- utiliser un fond violet profond avec accents or lumineux ;
- afficher un splash initial d'environ `0.95s a 1.1s` ;
- afficher une micro-transition premium de `300ms a 450ms` pendant les navigations ;
- fonctionner proprement sur iPhone, Android et desktop ;
- respecter `prefers-reduced-motion`.

## Approche retenue

L'approche retenue est `Jewel Reveal`.

Cette approche consiste a presenter un medaillon central contenant le logo existant LabeeB avec :

- un anneau dore ;
- un halo brillant autour du logo ;
- un balayage de lumiere traverse le medaillon ;
- une signature textuelle courte et elegante ;
- une disparition douce vers l'interface.

Cette approche est retenue car elle offre le meilleur equilibre entre :

- perception premium ;
- lisibilite de la marque ;
- compatibilite mobile ;
- cout technique limite.

## Comportement attendu

### Premier chargement

Au premier rendu d'une page, un overlay plein ecran couvre l'application.

Il contient :

- un fond premium violet royal avec lueurs dorees ;
- un medaillon circulaire centre ;
- le logo LabeeB existant ;
- le nom `LabeeB Arabic` ;
- une baseline courte et discrete ;
- un indicateur lumineux discret plutot qu'une barre de chargement classique.

Le splash reste visible assez longtemps pour etre perçu comme intentionnel, mais doit disparaitre rapidement. La cible est une duree totale visible de `0.95s a 1.1s`.

La fermeture du splash doit attendre :

- que le DOM soit pret ;
- que la duree minimale soit atteinte.

Il ne doit pas dependre d'un appel reseau specifique.

### Changements de page

Lors d'une navigation soft ou d'une soumission de formulaire geree par le shell, une version plus courte du meme langage visuel apparait.

Cette version reprend :

- le logo au centre ou legerement au-dessus du centre ;
- un halo et un eclat dore ;
- une opacity overlay plus legere que celle du splash initial ;
- une duree cible de `300ms a 450ms`.

Elle doit demarrer sur `app:navigation-start` et se fermer sur `app:navigation-stop` avec une duree minimale tres courte pour eviter les flashes brutaux.

## Direction visuelle

### Palette

- Violet profond comme base principale
- Or lumineux pour les accents premium
- Blanc chaud pour les textes secondaires
- Reflets transparents pour simuler une finition verre/joaillerie

### Composition

- Fond plein ecran avec gradients radiaux superposes
- Un coeur visuel central autour du logo
- Un anneau metallique fin
- Un halo externe anime
- Un balayage de lumiere sur le medaillon

### Style

Le loader doit evoquer :

- un produit premium ;
- une application mobile moderne ;
- une finition brillante et soignee ;
- une identite arabe/elegante sans surcharge decoratives.

Le design doit rester sobre. Aucun effet ne doit faire "jeu mobile agressif" ou "template de loader generique".

## Architecture technique

### Structure HTML

Le shell principal ajoutera une structure dediee au loader premium dans `base.html` :

- un overlay plein ecran pour le premier chargement ;
- un overlay de transition de navigation reconfigurable ;
- un conteneur central pour le logo, le texte et les effets.

Le logo existant `labeeb-logo-round.svg` sera reutilise.

### CSS

Les styles vivreont dans `app/static/css/main.css`.

Le CSS gerera :

- le fond premium ;
- les gradients et halos ;
- les animations d'entree et sortie ;
- les anneaux et reflets ;
- les variantes `boot`, `nav`, `hidden`, `active`, `leaving` ;
- les ajustements mobile et safe areas ;
- les fallbacks `prefers-reduced-motion`.

Les animations devront privilegier `opacity`, `transform` et `filter` legers pour rester fluides.

### JavaScript

Le pilotage vivra dans le shell global deja en place, avec un petit orchestration runtime dans `base.html` ou un script shell partage si le code devient trop long.

Le runtime devra :

- marquer le tout premier chargement ;
- afficher le splash boot immediatement ;
- attendre une duree minimale avant de le masquer ;
- ecouter `app:navigation-start` et `app:navigation-stop` ;
- gerer une duree minimale tres courte pour le loader de navigation ;
- nettoyer proprement tous les timers.

Le systeme ne doit pas ajouter d'etat persistant fragile ni casser les transitions existantes.

## Etats et transitions

### Etat boot

- visible des le chargement initial ;
- anime avec entree douce ;
- reste present au moins `950ms` ;
- disparait avec un fade-out premium.

### Etat nav

- utilise les evenements de navigation deja existants ;
- version plus compacte du meme composant ;
- duree minimale cible autour de `320ms`.

### Etat hidden

- overlay totalement inactif ;
- `pointer-events: none` ;
- impact nul sur la page.

### Motion reduite

Si l'utilisateur prefere reduire les animations :

- supprimer les balayages et pulsations ;
- conserver seulement un fade court ;
- garder l'information de chargement sans surcharge visuelle.

## Contraintes mobiles

### iPhone

- respecter `env(safe-area-inset-top)` et `env(safe-area-inset-bottom)` ;
- eviter les sauts visuels pendant l'apparition ;
- conserver le logo bien centre meme avec la barre Safari.

### Android

- garder une animation legere sur appareils milieu de gamme ;
- ne pas surutiliser blur et box-shadow lourds ;
- rester lisible sur ecrans tres lumineux.

### Responsivite

- taille du medaillon adaptee entre petits smartphones et desktop ;
- typographie compacte sur mobile ;
- aucun texte tronque de facon laide.

## Accessibilite

Le loader doit :

- rester purement decoratif si possible avec les bons attributs ARIA ;
- ne pas piger le focus clavier ;
- ne pas bloquer inutilement l'utilisateur apres chargement ;
- garder un contraste suffisant pour le texte du logo et de la signature.

## Strategie de test

Des tests de regression shell verifieront au minimum :

- presence du markup premium ;
- presence des classes/etats boot et nav ;
- presence des hooks d'evenements `app:navigation-start` et `app:navigation-stop` ;
- prise en charge d'une duree minimale pour le splash initial ;
- prise en charge d'une duree minimale pour la navigation ;
- prise en charge `prefers-reduced-motion`.

Une verification manuelle sera aussi necessaire sur :

- premier chargement ;
- navigation lien ;
- navigation formulaire ;
- iPhone ;
- Android ;
- connexion lente.

## Fichiers cibles

- `app/templates/base.html`
- `app/static/css/main.css`
- `app/static/js/native-nav.js` si besoin de garder le couplage evenementiel clair
- `tests/test_shell_resilience.py` ou un test shell dedie au loader premium

## Hors scope

- modification du logo source ;
- ajout de dependances JavaScript externes ;
- animation video ou Lottie ;
- refonte complete du systeme de navigation ;
- modification du fichier `moctar`.

## Risques et mitigations

### Risque 1

Un splash trop visible peut donner une impression de lenteur.

Mitigation :

- duree courte ;
- disparition des que le minimum premium est atteint ;
- version navigation plus breve encore.

### Risque 2

Des effets visuels trop lourds peuvent nuire aux performances mobiles.

Mitigation :

- limiter les blurs ;
- animer surtout `transform` et `opacity` ;
- fallback motion reduite ;
- nombre limite de couches decoratives.

### Risque 3

Le loader peut se desynchroniser avec la navigation.

Mitigation :

- reutiliser exclusivement les evenements shell deja normalises ;
- timers nettoyes ;
- etats explicites `boot` et `nav`.

## Definition de fini

La fonctionnalite sera consideree comme terminee quand :

- le premier chargement affiche un splash premium Jewel Reveal ;
- les changements de page affichent une micro-transition coherente ;
- le rendu est propre sur iPhone et Android ;
- le systeme respecte les preferences de motion reduite ;
- les tests shell mis a jour passent ;
- aucun changement n'est apporte a `moctar`.
