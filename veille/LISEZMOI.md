# Veille des règles

Surveille chaque mois les documents officiels utilisés par les packs de règles de Ligne 4 (FFN, FFN Maîtres, World Aquatics) et ouvre un ticket GitHub quand l'un d'eux change.

- `sources.json` : la liste des sources. Ajouter une source = ajouter un bloc ; `"actif": false` la met en pause.
- `veille.py` : le script (Python, sans dépendance).
- `etat.json` : créé et mis à jour automatiquement, ne pas modifier à la main.
- `.github/workflows/veille-regles.yml` : le calendrier (le 3 de chaque mois, rappel de saison le 2 septembre).

Lancer à la main : onglet **Actions** › **Veille des règles** › **Run workflow** (`verifier` ou `rappel`).

Un changement ne met rien à jour tout seul : il signale qu'il faut relire le document et, si besoin, publier un nouveau pack.
