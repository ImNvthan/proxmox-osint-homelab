# Contribuer

## Règles de base
- **Passif par défaut.** Tout ce qui touche activement un hôte tiers (scan,
  force brute, tentatives de connexion) doit rester derrière une option explicite
  + un avertissement. L'autopilote ne doit jamais devenir actif.
- **Données de tiers = opt-in.** Toute fonctionnalité qui collecte des données
  sur des personnes autres que la cible passe par un garde-fou du type
  `OSINT_ALLOW_RELATIONS` + confirmation.
- Pas d'exploitation, d'évasion, de résolution de CAPTCHA, de scraping derrière
  auth, de ciblage de masse.
- Chaque nouvel outil doit se dégrader proprement (`try`/`run`) : un binaire
  absent ou une étape en échec n'interrompt jamais le pipeline.

## Structure
```
ct/osint.sh              créateur côté hôte (mince)
misc/build.func          cadre de construction du LXC
misc/install.func        utilitaires d'installation
install/osint-install.sh provisionnement
tools/bin/*              CLI « osint » + autopilote + pipelines
tools/lib/common.sh      plomberie shell (case-aware)
tools/lib/osintkit/      moteur python
docs/*                   documentation
json/osint.json          métadonnées
```

## Boucle de dév
1. Éditez sur n'importe quelle machine.
2. `shellcheck -x -e SC1091 ct/*.sh install/*.sh misc/*.func tools/bin/* tools/lib/*.sh`
3. `python3 -m pyflakes tools/lib/osintkit/*.py` (ou `ruff check`).
4. Test rapide du moteur sans conteneur :
   ```bash
   PYTHONPATH=tools/lib python3 -m osintkit.classify "+33612345678"
   PYTHONPATH=tools/lib python3 -m osintkit.extract  <un_run_dir> --stdout
   ```
5. Test complet dans un LXC jetable :
   ```bash
   OSINT_REPO_URL="https://github.com/<vous>/proxmox-osint-homelab" \
   OSINT_REPO_BRANCH="ma-branche" bash install/osint-install.sh
   ```
6. PR contre `main`. La CI lance shellcheck.

## Ajouter un pipeline
- `tools/bin/osint-recon-<type>`, `chmod +x`, source `common.sh`,
  `new_run <type> <cible>` … `finish_run`.
- Brancher dans `tools/bin/osint`, `osint-report`, et — si l'autopilote doit
  savoir pivoter dessus — dans `osint-auto` (classification + `case`) et
  `osintkit/extract.py` (parseur de la sortie brute).
- Documenter dans `docs/WORKFLOWS.md` + `docs/TOOLS.md`.
