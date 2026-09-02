# L'autopilote

> Donnez ce que vous savez. L'outil détecte le type, enchaîne les pipelines,
> pivote sur ce qu'il découvre, et rend un graphe + une affiche.

## En une ligne

```bash
osint auto "+33612345678"
osint auto jean.dupont@gmail.com
osint auto jdupont77
osint auto "Jean Dupont" --ville Lyon
osint auto "Jean Dupont" --relations          # + famille / proches (garde-fou RGPD)
osint auto https://x.com/jdupont
```

Sans argument, `osint` pose la question :

```
$ osint
Que savez-vous ? (numéro / e-mail / pseudo / nom / domaine) : jean.dupont@gmail.com
Chercher aussi la famille/les proches ? [o/N] n
```

Ou l'interface web : `http://<ip-du-lxc>:8080` — un champ, un bouton.

## Ce qui se passe

1. **Classification** (`osintkit.classify`) : `+33…`→phone, `a@b.c`→email,
   `Jean Dupont`→person, `x.com/jdupont`→account, `acme.fr`→domain, `8.8.8.8`→ip.
2. **Enquête** créée dans `/opt/osint/cases/<id>/` avec un `graph.json`.
3. **File d'attente en largeur** : le sélecteur de départ est mis en file
   (profondeur 0).
4. Pour chaque élément : le pipeline `osint-recon-<type>` tourne, puis
   `osintkit.extract` lit `raw/` et écrit `selectors.jsonl`, puis
   `osintkit.graph merge` fusionne nœuds + liens dans `graph.json`.
5. Les **nouveaux** sélecteurs de confiance ≥ `--min-conf` sont mis en file à
   `profondeur + 1`, tant que `--depth` et `--nodes` (budget) ne sont pas
   atteints. `account plateforme/handle` → pivot en `username handle`.
6. `person` + `--relations` → `osint-recon-relations` ajoute des candidats
   famille/proches (mentions publiques + API open data) ; ils deviennent des
   nœuds `person` reliés par `family_of` / `related_to` avec une confiance basse.
7. **Consolidation** : `osintkit.graph render` (→ `graph.html`, `graph.svg`,
   `graph.json`) puis `osintkit.dossier` (→ `dossier.html` + un
   `entities/<nom>/dossier.html` par personne, `--pdf` pour le PDF).

## L'affiche (dossier une page)

Par personne :

```
NOM Prénom                                     [photo]
Identité   : Nom · Prénom · Naissance
             Téléphone (type, opérateur)          [sûr|probable|piste]
             E-mail                                [ … ]
             Adresse                               [ … ]
             Employeur / organisation              [ … ]
Réseaux sociaux : puces plateforme + lien + confiance
Famille / proches : sous-cartes (nom, lien, réseaux sociaux)
Sources & fiabilité
```

Chaque valeur porte un **niveau de confiance** :
`sûr` ≥ 0.7 · `probable` ≥ 0.45 · `piste` < 0.45. Rien n'est un fait tant que
vous ne l'avez pas recoupé.

## Réglages (drapeaux ou `/etc/osint/osint.env`)

| Drapeau | env | Défaut | Rôle |
|---|---|---|---|
| `--depth N` | `OSINT_AUTO_MAX_DEPTH` | 2 | profondeur de pivot |
| `--nodes N` | `OSINT_AUTO_MAX_NODES` | 40 | budget d'entités explorées |
| `--min-conf X` | `OSINT_AUTO_MIN_CONF` | 0.55 | seuil pour pivoter |
| `--relations` | `OSINT_ALLOW_RELATIONS=1` | off | famille / proches |
| `--case NOM` | — | auto-daté | nom de l'enquête |
| `--ville` / `--entreprise` | — | — | contexte person/relations |
| `--pdf` | — | off | dossier aussi en PDF (chromium) |
| `--yes` | `OSINT_ASSUME_YES=1` | off | pas de confirmation interactive |

## Reprendre / rejouer

```bash
osint case list
osint dossier <id>            # régénère l'affiche depuis graph.json
osint dossier <id> --pdf
osint graph   <id>            # régénère le graphe
osint case show <id>          # graph.json brut
osint case purge <id>         # effacement (RGPD)
```

Relancer `osint auto <même valeur> --case <id>` réutilise l'enquête : le graphe
est cumulatif.

## Limites connues

- Précision ≠ exhaustivité : sans clés d'API, on dépend de sources publiques
  bruyantes. Ajoutez des clés (`docs/API-KEYS.md`).
- L'« adresse » n'est fiable que si elle apparaît littéralement dans une source
  publique (bio, whois non masqué, page indexée). Sinon : ville/région au mieux.
- La résolution pseudo→identité réelle est heuristique (profil GitHub/Gravatar,
  parsing maigret). À valider.
- `relations` fait des requêtes de moteur de recherche : lent (temporisé par
  courtoisie) et sensible aux limites de débit.
