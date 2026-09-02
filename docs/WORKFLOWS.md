# Flux de travail

## Le raccourci : l'autopilote

```bash
osint auto "<ce que vous savez>"        # voir docs/AUTOPILOT.md
```

Sortie dans `/opt/osint/cases/<id>/` :

```
graph.json        graphe d'entités (import Maltego/Gephi)
graph.html        graphe rendu (svg via graphviz)
dossier.html      dossier maître (toutes les personnes)
entities/<nom>/dossier.html   une affiche par personne (+ .pdf avec --pdf)
runs/             les exécutions unitaires (report.html + raw/ + selectors.jsonl)
engine.log        journal de l'autopilote
status            étape en cours
```

Tout parcourir : `osint serve` → `http://<ip>:8899` (sert `runs/` **et**
`cases/`), ou l'interface web `http://<ip>:8080`.

---

## Pipelines unitaires

Chaque pipeline écrit `/opt/osint/runs/<type>_<cible>_<ts>/` (hors enquête) et
produit `report.html` + `selectors.jsonl`.

### Numéro de téléphone
```bash
osint phone +33612345678
```
parse E.164 (opérateur / type / région) + phoneinfoga + ignorant + dorks FR.

### E-mail
```bash
osint email jean.dupont@gmail.com
```
holehe + socialscan + h8mail + Gravatar (hash + profil) + GHunt + DMARC/MX.
Avec `HIBP_API_KEY` : Have I Been Pwned.

### Pseudo
```bash
osint username jdupont
```
sherlock + maigret (rapport HTML + JSON riche) + blackbird + socialscan +
GitHub/GitLab/Keybase. Produit `candidate-emails.txt`.

### Personne → pivots
```bash
osint person "Jean Dupont" --entreprise acme.fr --ville Lyon
osint person "Jean Dupont" --deep         # balaie chaque pseudo candidat
```
Permutations pseudos/e-mails (via `osintkit.normalize`) + `dorks.md` prêt à
coller + récolte theHarvester si `--entreprise`.

### Famille / proches  (garde-fou)
```bash
OSINT_ALLOW_RELATIONS=1 osint relations "Jean Dupont" --ville Lyon
# ou :  osint relations "Jean Dupont" --autoriser
```
Dorks + DuckDuckGo HTML (sans clé) + API `recherche-entreprises.api.gouv.fr` →
`relations.json` : candidats co-mentionnés avec un mot de parenté ou le même nom.
**Non vérifié.** Refuse de tourner sans autorisation explicite.

### Domaine / IP
```bash
osint domain acme.fr           # + --active pour nmap (autorisé uniquement)
osint ip 1.2.3.4               # ou 1.2.3.0/24
```

---

## Enquêtes

```bash
osint case list
osint case show <id>          # graph.json
osint case open <id>          # chemins + URL web
osint dossier <id> [--pdf]    # régénère l'affiche
osint graph   <id>            # régénère le graphe
osint case purge <id>         # effacement RGPD
```

## Surveillance planifiée

```bash
osint monitor add auto "Jean Dupont"       # autopilote quotidien, alerte au changement
osint monitor add domain acme.fr
osint monitor list
systemctl list-timers 'osint-*'
```
`OSINT_NOTIFY_CMD` dans `osint.env` reçoit l'alerte sur stdin (ex. ntfy/Slack).

## Rétention (RGPD)

```bash
# dans /etc/osint/osint.env
OSINT_CASE_TTL_DAYS="30"
# puis
systemctl enable --now osint-case-gc.timer
```

## Sortie anonymisée

```bash
torsocks osint auto jean.dupont@gmail.com
```

## SpiderFoot (corrélation lourde)

```bash
osint spiderfoot status
osint spiderfoot expose            # -> http://<ip>:5001 (sans auth, LAN uniquement)
osint spiderfoot scan acme.fr
```

## Mise à jour

```bash
osint-update      # OS + pipx + Go + SpiderFoot + moteur + dépôt (aussi timer hebdo)
```
