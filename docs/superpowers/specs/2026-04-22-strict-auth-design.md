# Strict Auth Design

**Goal**

Simplifier l'authentification en gardant une inscription publique uniquement pour les etudiants, avec validation manuelle par un admin avant toute connexion.

**Regles produit**

- Etudiant:
  - inscription publique via une page `register`
  - connexion uniquement avec `email + mot de passe`
  - compte cree en `en_attente`
  - acces autorise seulement apres validation admin
- Enseignant:
  - pas d'inscription publique
  - compte cree uniquement par un admin
  - connexion avec `email + mot de passe`
- Admin:
  - pas d'inscription publique
  - compte cree par un autre admin
  - connexion avec `email + mot de passe`

**Impact technique**

- Le champ `Utilisateur.statut` devient la source de verite pour l'activation des comptes.
- Le login n'accepte plus le telephone comme identifiant.
- Le login public ne propose plus Google OAuth.
- Une nouvelle route publique `register` cree toujours un compte `eleve` en `en_attente`.
- Une nouvelle vue admin `valider-comptes` liste les etudiants en attente et permet de les activer.

**Parcours**

1. Un visiteur ouvre `register`.
2. Il remplit nom, prenom, email, mot de passe, confirmation.
3. Le systeme cree un utilisateur `role=eleve`, `statut=en_attente`.
4. Tant qu'un admin ne valide pas ce compte, le login refuse la connexion avec un message clair.
5. L'admin ouvre `admin/valider-comptes`, voit la liste des comptes en attente, puis clique sur `Valider`.
6. L'etudiant peut ensuite se connecter normalement.

**Contraintes de migration**

- Les comptes existants restent utilisables.
- Les comptes crees par admin pour `enseignant` et `admin` doivent etre `actif` par defaut.
- Aucun changement ne doit casser le flux de reinitialisation de mot de passe.

**UI admin**

- Une page dediee affiche uniquement les etudiants `en_attente`.
- Chaque ligne montre email, date d'inscription, et un bouton `Valider`.
- La liste doit rester simple, lisible et responsive.

**Tests attendus**

- `register` cree un etudiant `en_attente`.
- Un etudiant `en_attente` ne peut pas se connecter.
- Un login par telephone echoue.
- Un admin voit la liste des comptes a valider.
- Le clic `Valider` active le compte.
- Un etudiant valide peut se connecter.
