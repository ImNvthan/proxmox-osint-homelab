# Journal des modifications

Format librement inspiré de [Keep a Changelog](https://keepachangelog.com/).

## [2.0.1] - 2026-09-03

### Corrigé
- Installation : `git clone` remplacé par un téléchargement d'archive `tar.gz`
  via `curl --retry` (`fetch_src`) pour la charge utile du dépôt **et** pour
  SpiderFoot — évite l'échec quand GitHub limite les requêtes git anonymes
  (l'install se retrouvait sans CLI). `GIT_TERMINAL_PROMPT=0` partout : plus
  d'invite d'identifiants bloquante.
- `osint-update` sait se mettre à jour sans dépôt git local (archive `tar.gz`).
- `retry` sur `theHarvester` / `recon-ng` (pipx) et sur la liste de mots SecLists.
- Si la charge utile `tools/` est introuvable, l'installateur échoue franchement
  avec la commande de reprise, au lieu de continuer un conteneur inutilisable.

## [2.0.0] - 2026-09-03

Réécriture orientée **homelab / autopilote**. Repart de la base v1
(`proxmox-osint-lxc`) — même cadre de construction Proxmox, mêmes pipelines
passifs — et ajoute par-dessus un moteur d'orchestration.

### Ajouté
- **Autopilote `osint auto <valeur>`** : détection du type de sélecteur
  (numéro / e-mail / pseudo / nom / domaine / IP / URL), enchaînement automatique
  des pipelines, pivot en largeur borné (`--depth`, `--nodes`, `--min-conf`) sur
  les sélecteurs découverts.
- **Moteur `osintkit`** (python, `tools/lib/osintkit/`) :
  `classify`, `normalize` (E.164 via phonenumbers, URL→plateforme),
  `extract` (sortie brute d'un outil → `selectors.jsonl`),
  `graph` (`graph.json` : nœuds/liens, fusion, rendu graphviz + export Maltego/Gephi),
  `relations` (proches/famille via dorks + DuckDuckGo HTML + API open data),
  `dossier` (affiche HTML + PDF chromium), `web` (interface Flask).
- **Notion d'enquête** `/opt/osint/cases/<id>/` : `graph.json`, `dossier.html`,
  `entities/<nom>/dossier.html`, `graph.html`, `runs/`, `engine.log`, `status`.
- **L'affiche** : carte une page par personne — nom, prénom, téléphone (type +
  opérateur), e-mail, adresse, employeur, réseaux sociaux, **famille / proches**,
  chaque champ avec un niveau de confiance.
- **Interface web** (`osint web`, systemd `osint-web.service`, :8080) : un champ
  de saisie → autopilote en arrière-plan → dossier + graphe.
- **`osint-recon-relations`** + `osint-recon-phone` enrichi (parse E.164),
  `osint-recon-username` (+ blackbird), pipeline `relations` dans `osint-report`.
- **Commandes** : `osint case {list,show,open,dossier,graph,purge}`,
  `osint dossier`, `osint graph`, `osint web {start,expose,local,status}`.
- **Garde-fous** : confirmation avant traitement de données personnelles,
  `--relations` désactivé par défaut (`OSINT_ALLOW_RELATIONS`), `osint case purge`,
  rétention `OSINT_CASE_TTL_DAYS` + `osint-case-gc.timer`.
- Docs : `AUTOPILOT.md`, `ARCHITECTURE.md` ; `LEGAL.md` réécrit avec le cadre
  RGPD / Code pénal français et une section dédiée à la fonction famille/proches.

### Modifié
- Conteneur par défaut : 6→8 Gio RAM, 30→40 Go disque (moteur + chromium + deps).
- `common.sh` devient *case-aware* : `new_run`/`finish_run` rangent l'exécution
  dans l'enquête courante et déclenchent extraction + fusion dans le graphe.
- `osint-update` copie aussi `osintkit/` et redémarre l'interface web.
- Dépôt renommé `proxmox-osint-homelab` (les URLs par défaut suivent).

### Repris de la v1 sans changement de fond
- `ct/osint.sh`, `misc/build.func`, `misc/install.func`, pipelines
  `domain`/`ip`/`person`, `osint-monitor`, timers d'update, SpiderFoot en service.
