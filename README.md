# Codex Updates — centrale technique

Dépôt destiné aux métadonnées **publiques** des versions du Lab Codex.

- `index.json` liste les applications publiques.
- `apps/<id>/latest.json` indique la version publiée, le lien HTTPS direct de téléchargement, le SHA-256 et les nouveautés.
- `version: null` et `download_url: null` signifient « pas de version publiée ». Ne pas activer le bouton Télécharger dans cet état.
- Pour publier une version, déposer l'APK/EXE dans un emplacement de distribution (par exemple GitHub Releases), calculer son SHA-256, puis actualiser **uniquement** le manifeste de l'application.
- Le Lab lit `index.json` puis chaque manifeste. Une application vérifie directement son manifeste.
- Les fichiers JSON doivent être servis via HTTPS avec CORS autorisé (GitHub Pages convient pour un Lab sur un autre domaine).
- Ne jamais mettre d'APK privée ni de lien secret dans un dépôt public : les fichiers et l'historique Git sont publics.
- Le JSON n'est pas une preuve de confiance : vérifier HTTPS, SHA-256, version/build et signature de l'application avant toute installation.
- Les fichiers sont des **gabarits** : aucun téléchargement n'est encore opérationnel tant que les releases ne sont pas renseignées.

## Déploiement
Créer un dépôt public `codex-updates`, copier le contenu de ce dossier à sa racine, activer GitHub Pages (branche main, racine `/`). URL attendue : `https://<utilisateur>.github.io/codex-updates/index.json`.
