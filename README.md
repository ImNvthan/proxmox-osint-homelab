<div align="center">

```
   ___  ____ ___ _   _ _____
  / _ \/ ___|_ _| \ | |_   _|
 | | | \___ \| ||  \| | | |
 | |_| |___) | || |\  | | |
  \___/|____/___|_| \_| |_|
```

# Homelab OSINT — LXC Proxmox VE, autopilote

**Une commande sur l'hôte Proxmox → un conteneur Debian non privilégié avec un
vrai homelab OSINT. Vous saisissez ce que vous savez ; il cherche seul.**

Inspiré de [community-scripts.org](https://community-scripts.org) · licence MIT ·
[Usage légal et éthique](docs/LEGAL.md)

</div>

---

## L'idée

> J'ouvre le LXC, je mets l'info que j'ai (un numéro, un e-mail, un nom), et ça
> recherche automatiquement tout ce qui est lié — jusqu'à une **affiche** :
> nom, prénom, numéro, e-mail, adresse, réseaux sociaux. Et pareil pour la
> famille / les proches.

C'est exactement ce que fait `osint auto`. Le type du sélecteur est détecté, les
pipelines de reconnaissance passive s'enchaînent, l'outil **pivote** sur ce qu'il
trouve (un e-mail mène à des comptes, un compte à un pseudo, un pseudo à un nom…),
construit un **graphe d'entités** et rend une **affiche par personne**.

---

## Installation

Sur l'hôte **Proxmox VE** (root) :

```bash
bash -c "$(wget -qLO - https://raw.githubusercontent.com/ImNvthan/proxmox-osint-homelab/main/ct/osint.sh)"
```

Menu (Par défaut / Avancé) → `pct create` → installation entièrement automatisée
dans le conteneur. À la fin : IP + mot de passe root aléatoire.

**Conteneur par défaut :** Debian 12 · non privilégié · 4 vCPU · 8 Gio RAM ·
40 Go · `nesting=1`. Proxmox VE 8.x / 9.x, amd64. Compter 15–30 min d'install
(compilations Go, pip, SpiderFoot).

Sans Proxmox : `install/osint-install.sh` tourne sur toute Debian 12 / Ubuntu
22.04+ **qui vous appartient**.

---

## Utilisation

```bash
pct enter <ctid>

osint                                   # invite : « Que savez-vous ? »
osint auto "+33612345678"               # autopilote en une ligne
osint auto jean.dupont@gmail.com
osint auto "Jean Dupont" --ville Lyon --relations
```

Ou l'**interface web** : `http://<ip-du-lxc>:8080` — un champ, un bouton.
(`osint web expose` pour l'ouvrir au LAN ; posez `OSINT_WEB_USER/PASS` d'abord.)

### Ce que produit une enquête — `/opt/osint/cases/<id>/`

| Fichier | Contenu |
|---|---|
| `dossier.html` | **l'affiche** : une carte par personne — identité, téléphone, e-mail, adresse, employeur, **réseaux sociaux**, **famille / proches** |
| `entities/<nom>/dossier.html` (+ `.pdf`) | l'affiche d'une seule personne |
| `graph.html` / `graph.json` | graphe d'entités (import Maltego / Gephi / yEd) |
| `runs/…/report.html` | le détail brut de chaque pipeline |

Chaque valeur porte un niveau de confiance : `sûr` · `probable` · `piste`.

---

## Ce qu'il contient

**Autopilote** (`osint auto`) : classification du sélecteur → BFS bornée
(`--depth`, `--nodes`) → extraction de sélecteurs → graphe → affiche.
Détail : [docs/AUTOPILOT.md](docs/AUTOPILOT.md).

**Pipelines unitaires** : `domain` · `username` · `email` · `phone` · `person` ·
`ip` · `relations`. Chacun → `report.html` + `selectors.jsonl`.

**Moteur** `osintkit` (python) : `classify` · `normalize` (E.164, plateformes) ·
`extract` · `graph` · `relations` · `dossier` · `web`.

**Outils** : sherlock, maigret, blackbird, holehe, socialscan, h8mail,
phoneinfoga, ignorant, theHarvester, subfinder/httpx/dnsx, gowitness, dnstwist,
checkdmarc, SpiderFoot (service), recon-ng, Tor… — liste :
[docs/TOOLS.md](docs/TOOLS.md).

**En plus** : `osint monitor` (surveillance + alerte), `osint-update` (timer
hebdo), `osint case purge` + `osint-case-gc.timer` (rétention RGPD),
`torsocks osint …` (sortie anonymisée).

---

## Garde-fous

- **Passif par défaut.** L'autopilote ne fait jamais de scan actif ; `--active`
  (nmap) n'existe que sur `domain`/`ip`, avec avertissement.
- **Confirmation** avant tout traitement de données personnelles (sauf `--yes`).
- **Famille / proches désactivée par défaut** — `--relations` ou
  `OSINT_ALLOW_RELATIONS=1` vaut déclaration de base légale (RGPD).
- **Purge** : `osint case purge <id>` ; TTL automatique via `OSINT_CASE_TTL_DAYS`.
- **Tout en local** : web et SpiderFoot sur `127.0.0.1` tant que vous ne les
  exposez pas.

À lire : [docs/LEGAL.md](docs/LEGAL.md).

---

## Structure du dépôt

```
ct/osint.sh                 à lancer sur l'hôte Proxmox
misc/build.func             cadre de construction du LXC
misc/install.func           utilitaires d'installation dans le conteneur
install/osint-install.sh    provisionnement (apt + Go + pipx + SpiderFoot + moteur + CLI)
tools/bin/osint*            la CLI, l'autopilote et les pipelines
tools/lib/common.sh         plomberie shell partagée (case-aware)
tools/lib/osintkit/         moteur python (classify/extract/graph/dossier/relations/web)
tools/systemd/*             services & timers (web, update, monitor, case-gc)
tools/etc/*                 osint.env.example, motd
docs/                       AUTOPILOT · ARCHITECTURE · TOOLS · WORKFLOWS · API-KEYS · LEGAL
json/osint.json             métadonnées du script utilitaire
```

## Depuis un clone (dév / quasi hors-ligne)

```bash
git clone https://github.com/ImNvthan/proxmox-osint-homelab
cd proxmox-osint-homelab
bash ct/osint.sh
# pointer le conteneur vers votre fork :
OSINT_REPO_URL=https://github.com/vous/proxmox-osint-homelab OSINT_REPO_BRANCH=dev bash ct/osint.sh
```

## Crédits

Ergonomie de construction inspirée de
[Proxmox VE Community Scripts](https://github.com/community-scripts/ProxmoxVE).
Les outils fournis appartiennent à leurs auteurs — SpiderFoot, ProjectDiscovery,
sherlock, maigret, blackbird, holehe, theHarvester, dnstwist, phoneinfoga, et
bien d'autres.

## Licence

[MIT](LICENSE) © 2026 Nathan Drancourt. Aucune garantie. À utiliser de façon
responsable et licite.
