# Refonte Chaleureuse Du Menu Mobile

**Objectif**

Donner au menu mobile de LabeeB Arabic une identite plus premium, plus chaleureuse et plus memorable sans casser la navigation existante ni la logique des roles.

**Constat**

Le menu actuel fonctionne, mais il reste visuellement plat:
- le logo n'a pas de vraie presence de marque
- le nom de marque manque de chaleur
- le bouton hamburger ressemble a un controle Bootstrap standard
- les liens du menu mobile n'ont pas encore un rendu "section premium"
- la carte profil est lisible mais pas distinctive

**Direction visuelle**

La refonte retient une direction `warm premium`:
- logo rond avec effet medaillon
- nom de marque plus doux et plus accueillant
- petit sous-texte de marque pour renforcer la chaleur
- hamburger transforme en bouton capsule premium
- panneau mobile plus profond avec verre, ombres et reflets subtils
- liens transformes en boutons de section plus elegants
- profil utilisateur affiche dans une vraie mini-carte

**Structure**

Les changements restent limites a la navigation globale:
- `app/templates/base.html`
- `app/static/css/main.css`
- `tests/test_navigation_shell.py`

**Comportement**

La logique metier du menu ne change pas:
- les liens visibles restent controles par le role
- le role `eleve` ne doit toujours pas voir `Dashboard`
- les routes, endpoints et dropdowns restent inchanges

**Elements cles**

1. Bloc marque:
- medaillon rond CSS-only
- titre de marque en deux tons
- signature textuelle chaleureuse

2. Bouton hamburger:
- trois lignes custom
- transformation visuelle lorsque le menu est ouvert

3. Panneau mobile:
- conteneur plus riche visuellement
- coins plus arrondis
- fond degrade et bordure douce

4. Actions de navigation:
- icones dans des petits supports ronds
- hover/active plus premium
- carte profil avec avatar texte et badge de role

**Verification**

La verification doit confirmer:
- le role `eleve` ne voit toujours pas `Dashboard`
- le menu rendu contient les nouveaux marqueurs de design (`brand-mark`, `brand-tagline`, `nav-profile-avatar`)
- la suite de tests de navigation reste verte
