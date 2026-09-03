# Journal des modifications

Format librement inspiré de [Keep a Changelog](https://keepachangelog.com/).

## [2.0.3] - 2026-09-03

### Corrigé (bugs vus en test réel sur un nom à forte empreinte)
- **`rc=127` sur github/gitlab/keybase** : `oget` (fonction shell) n'existait pas
  dans le `bash -c` de `run_sh`. `oget` est désormais `export -f`, et
  `osint-recon-username` appelle `curl` directement.
- **Cascade de faux positifs** : l'autopilote pivotait sur les bouts d'URL de
  sherlock (`add`, `people`, `profile`, `emmanuelmacron?uselang=qqx`…) → 25 runs
  inutiles. `enqueue_from_run` ne pivote plus QUE sur `email`, `person_name`, et
  les pseudos issus des permutations/websearch (max 3, format validé, liste noire
  de mots génériques). **Plus aucun pivot depuis un compte trouvé.**
- **sherlock trop bruité** : `extract` ne garde que les comptes sur plateformes
  connues, en confiance 0.5 (« piste », jamais pivoté), plafonné à 30.
- **maigret `rc=1` systématique** : invocation réduite au minimum (`-J simple`
  seul, sans `-T`/`-H`/`ndjson`/double run) ; le bavardage part dans
  `logs/maigret-tool.log`.
- **`websearch results: []`** : bascule sur `lite.duckduckgo.com` (plus fiable
  depuis un datacenter) avec repli sur l'endpoint HTML.

## [2.0.2] - 2026-09-03

### Ajouté
- `osintkit.websearch` : recherche web pour `osint-recon-person` (et `relations`),
  ordre de priorité **Google CSE (100/jour) → SerpAPI (100/mois) → DuckDuckGo
  (sans clé)**. Sort les profils **LinkedIn / Twitter / Instagram / GitHub…** à
  partir d'un nom. Clés : `GOOGLE_CSE_KEY` + `GOOGLE_CSE_CX` (voir docs/API-KEYS).
- Affiche : **chaque réseau social est un lien cliquable** (URL complète). Les
  comptes détectés sans handle (holehe/socialscan) reçoivent une URL reconstruite
  depuis un pseudo connu, marquée « URL déduite ».

### Corrigé
- **Classification** : un `+33…` ou un e-mail *au milieu d'une phrase* est
  maintenant reconnu (« ton numéro en +33681038820 » → `phone +33681038820`,
  plus « person: ton numéro en… » qui fabriquait `tonnumeroen…@gmail.com`).
  Gère aussi `06 12 34 56 78`, `06.12.34.56.78`.
- **Pivot nom → réseaux sociaux** : `osint-recon-person` promeut ses 5 meilleurs
  pseudos candidats en sélecteurs `username` (conf. 0.58) → l'autopilote les
  relance vraiment dans `sherlock`/`maigret`. Avant, il ne pivotait jamais.
- **Numéro → opérateur / type / région** : `extract` lit `phone-parse.json`
  (python-phonenumbers) et enrichit le nœud téléphone ; l'affiche affiche
  « +33… (mobile, Orange France, France) ».
- **Moins de bruit** : les permutations synthétiques (`emails.txt`,
  `usernames.txt`, `permutations.json`, `websearch.json`) ne sont plus
  ré-aspirées par le balayage regex générique ; l'affiche plafonne les longues
  listes de « pistes » avec un « + N non vérifiées ».
- `extract` : `push()` fusionne désormais `attrs`/`url`/confiance dans une entrée
  existante au lieu de jeter le doublon.

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
