# Support Reset Chat Design

**Goal**

Remplacer la reinitialisation par email par un fil de support interne unique par etudiant, utilisable a la fois depuis les pages etudiant et depuis le parcours `Mot de passe oublie ?`, avec validation manuelle par un admin avant emission d'un lien de reinitialisation valable 30 minutes.

**Regles produit**

- Un seul fil de support par etudiant.
- Tous les admins voient tous les fils et peuvent repondre.
- Les messages doivent rester consultables au moins 3 mois.
- Le bouton `Mot de passe oublie ?` ne doit plus envoyer d'email.
- Une demande de reinitialisation cree automatiquement un message systeme dans le fil.
- Les admins recoivent une notification dans la cloche pour chaque nouvelle demande de reinitialisation et pour les nouveaux messages etudiant.
- Un admin peut discuter avec l'etudiant dans le fil, puis cliquer `Accorder 30 min`.
- Le clic `Accorder 30 min` genere un token de reinitialisation, ajoute un message systeme dans le fil, et expose le lien complet uniquement a l'etudiant.
- L'etudiant clique sur ce lien depuis le fil et arrive sur la page finale de nouveau mot de passe.

**Parcours principal**

1. L'etudiant clique `Mot de passe oublie ?` depuis la page de connexion.
2. Une page de support lui demande son email.
3. Si l'email existe, le systeme cree ou reutilise le fil de support associe a cet etudiant.
4. Le systeme enregistre aussi un acces invite signe pour ce navigateur, afin que l'etudiant puisse lire et ecrire dans ce fil sans etre connecte.
5. Le systeme ajoute un message systeme de type `reset_requested` dans le fil.
6. Le systeme cree une notification admin avec lien vers le fil.
7. Un admin ouvre le fil depuis la cloche, pose des questions si besoin, puis clique `Accorder 30 min`.
8. Le systeme cree un token securise valable 30 minutes, l'associe a une autorisation de reset, puis ajoute un message systeme dans le fil.
9. L'etudiant voit le lien de reinitialisation dans son fil, clique dessus, puis change son mot de passe sur la page publique de reset.

**Experience etudiant**

- Etudiant connecte:
  - peut ouvrir son fil de support depuis ses pages
  - voit l'historique des echanges
  - peut envoyer un message libre
- Etudiant non connecte:
  - peut acceder au fil de reset seulement depuis le navigateur qui a lance la demande
  - ne voit que son propre fil
  - peut lire les messages admin et envoyer des reponses dans cette conversation

**Experience admin**

- Tous les admins voient une liste des fils support.
- Les fils les plus recents et ceux avec demandes de reset non traitees remontent en tete.
- L'admin voit pour chaque fil:
  - nom et email de l'etudiant
  - derniere activite
  - dernier message
  - etat de reset en attente ou accorde
- Dans le fil, l'admin peut:
  - envoyer un message
  - voir l'origine de la derniere demande de reset avec IP et user agent si disponibles
  - cliquer `Accorder 30 min`

**Architecture**

- `SupportThread` represente le fil unique d'un etudiant.
- `SupportMessage` stocke chaque message du fil, qu'il soit humain ou systeme.
- `PasswordResetGrant` stocke l'autorisation de reset, le token, son expiration, l'admin createur, et son etat d'utilisation.
- La cloche existante continue a utiliser la table `Notification` pour prevenir les admins.
- Le reset final continue a reutiliser la page publique `/reset_password/<token>`, mais le token n'est plus emis par email.

**Modele de donnees**

- `SupportThread`
  - `student_id`
  - `status` (`open`, `closed`)
  - `last_activity_at`
  - `last_reset_requested_at`
  - `last_reset_granted_at`
  - `created_at`
  - `updated_at`
- `SupportMessage`
  - `thread_id`
  - `author_user_id` nullable pour les messages systeme
  - `author_role` (`student`, `admin`, `system`)
  - `message_type` (`message`, `reset_requested`, `reset_granted`)
  - `body`
  - `payload_json`
  - `created_at`
- `PasswordResetGrant`
  - `thread_id`
  - `student_id`
  - `granted_by_admin_id`
  - `token`
  - `expires_at`
  - `used_at`
  - `request_ip`
  - `request_user_agent`
  - `created_at`

**Securite**

- Le lien de reset reste un token signe et expire au bout de 30 minutes.
- L'acces au fil non connecte se fait via un cookie ou une session signee, cree lors de la demande `Mot de passe oublie ?`.
- Les admins ne voient pas le lien complet de reset dans le chat; ils voient seulement qu'une autorisation a ete accordee.
- L'etudiant ou l'invite autorise voit le vrai lien dans le message systeme.
- L'IP et le user agent de la demande sont journalises et affiches aux admins comme signal de verification, mais ne servent pas a bloquer strictement le reset.

**Notifications**

- Nouvelle demande de reset:
  - une notification est creee pour tous les admins
  - titre type: `Nouvelle demande de reinitialisation`
  - CTA vers le fil support de l'etudiant
- Nouveau message etudiant dans un fil:
  - notification admin si le dernier auteur n'est pas admin
- La notification n'est pas un doublon si l'evenement vient du meme message systeme ou du meme message chat.

**Retention**

- Les messages et autorisations restent en base au moins 90 jours.
- En premiere version, aucun job de suppression automatique n'est necessaire; conserver plus longtemps est acceptable.

**Migration**

- Le flux `/request_reset_password` est conserve en URL mais change de comportement.
- Le flux `/reset_password/<token>` reste la page finale de changement de mot de passe.
- L'envoi d'email de reset est retire du code et n'est plus utilise par ce parcours.
- Le helper d'email peut etre supprime si aucun autre usage actif n'existe encore apres verification.

**Contraintes techniques**

- Le nouveau chat doit s'integrer au systeme de cloche et a l'inbox existants.
- Les routes publiques de support invite doivent etre ajoutees aux exemptions auth/onboarding pertinentes.
- Le rendu doit rester simple et responsive sur mobile.
- Le premier livrable privilegie la solidite et la lisibilite plutot que le temps reel.

**Hors scope**

- WebSocket ou temps reel live
- Pieces jointes
- Attribution d'un fil a un admin unique
- Multiples fils par etudiant
- Effacement automatique des conversations a exactement 90 jours

**Tests attendus**

- Une demande `Mot de passe oublie ?` cree un message systeme et un acces invite.
- Tous les admins recoivent une notification pour la demande.
- Un admin peut repondre dans le fil.
- Un admin peut accorder un reset 30 minutes.
- Le message de lien de reset n'expose le token qu'a l'etudiant ou l'invite autorise.
- Un token expire ou deja utilise est refuse.
- Le reset final met bien a jour le mot de passe.
- Le lien `Mot de passe oublie ?` n'utilise plus `envoyer_email`.
