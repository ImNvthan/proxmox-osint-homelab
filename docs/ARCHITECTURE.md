# Architecture

```
HÔTE PROXMOX
  ct/osint.sh ──charge──> misc/build.func ──> pct create + pct start
                                           └─> pct exec: curl install/osint-install.sh | bash
                                                          └─ misc/install.func (try/pipx/go helpers)

CONTENEUR (Debian 12, non privilégié, nesting=1)
  /usr/local/bin/osint*            CLI + pipelines (bash)
  /opt/osint/lib/common.sh         plomberie (run/timeout/manifest, case-aware)
  /opt/osint/lib/osintkit/         MOTEUR python (classify/extract/graph/dossier/relations/web)
  /opt/osint/runs/                 exécutions hors enquête
  /opt/osint/cases/<id>/           enquêtes de l'autopilote
  /opt/spiderfoot/                 SpiderFoot (systemd, 127.0.0.1:5001)
  systemd: spiderfoot · osint-web(:8080) · osint-update.timer · osint-monitor@ · osint-case-gc.timer
```

## CLI (bash) — `tools/bin/`

| Binaire | Rôle |
|---|---|
| `osint` | routeur : `auto`, `case`, `web`, `dossier`, `graph`, `domain`…, `doctor`, `update` |
| `osint-auto` | **autopilote** : classifie, BFS bornée, appelle les pipelines, consolide |
| `osint-recon-{domain,username,email,phone,person,ip}` | pipelines de reconnaissance passive |
| `osint-recon-relations` | famille/proches (garde-fou `OSINT_ALLOW_RELATIONS`) |
| `osint-report` | 1 exécution → `report.md` + `report.html` autonome |
| `osint-monitor` | surveillance planifiée + alerte au changement |
| `osint-update` | OS + pipx + Go + SpiderFoot + moteur + dépôt |
| `osint-case-gc` | purge des enquêtes expirées (`OSINT_CASE_TTL_DAYS`) |

## Moteur (python, sans dépendance obligatoire) — `tools/lib/osintkit/`

| Module | Rôle | Dépend de (facultatif) |
|---|---|---|
| `classify.py` | type d'un sélecteur saisi | — |
| `normalize.py` | téléphones E.164, e-mails, pseudos, URLs→plateforme, noms | `phonenumbers` |
| `extract.py` | `raw/` d'une exécution → `selectors.jsonl` | — |
| `graph.py` | modèle `graph.json` (nœuds/liens), fusion, rendu | `graphviz` (`dot`) |
| `relations.py` | dorks + recherche web sans clé + API annuaire-entreprises → candidats proches | `requests` |
| `dossier.py` | `graph.json` → affiche HTML (+ PDF chromium) | `jinja2`, `chromium` |
| `web.py` | interface Flask (saisie → `osint auto` → dossier) | `flask` |

`osint doctor` vérifie chaque binaire **et** chaque module python.

## Modèle de données — `graph.json`

```json
{
  "case": "case_20260903-101500_ab12",
  "seed": {"kind": "phone", "value": "+33612345678"},
  "nodes": [
    {"id":"person:jean-dupont","kind":"person","label":"DUPONT Jean",
     "attrs":{"first_name":"Jean","last_name":"Dupont"},
     "sources":["run:phone_...","seed"],"confidence":0.8},
    {"id":"account:twitter/jdupont","kind":"account",
     "attrs":{"platform":"twitter","handle":"jdupont","url":"https://x.com/jdupont"},
     "sources":["maigret"],"confidence":0.8}
  ],
  "edges": [
    {"src":"person:jean-dupont","dst":"account:twitter/jdupont","rel":"uses","confidence":0.8},
    {"src":"person:jean-dupont","dst":"person:marie-dupont","rel":"family_of",
     "subtype":"même nom de famille","confidence":0.45}
  ]
}
```

`kind` ∈ person·email·phone·username·account·address·organization·domain·ip·url·photo
`rel` ∈ owns·uses·same_as·member_of·works_at·related_to·family_of·mentions·resolves_to·seed

`graph.json` s'importe tel quel dans Maltego / Gephi / yEd (nœuds + liste d'arêtes).

## Flux d'une exécution dans une enquête

```
osint-auto  ──export OSINT_CASE, OSINT_ANCHOR──>  osint-recon-<type>
   └─ common.sh:new_run     -> cases/<id>/runs/<type>_<cible>_<ts>/{raw,logs,meta.env,manifest.tsv}
   └─ common.sh:finish_run  -> osint-report                 (report.html)
                            -> osintkit.extract             (selectors.jsonl)
                            -> osintkit.graph merge          (graph.json += )
osint-auto lit selectors.jsonl -> met en file les nouveaux sélecteurs (depth+1)
... boucle ...
osint-auto -> osintkit.graph render -> osintkit.dossier
```
