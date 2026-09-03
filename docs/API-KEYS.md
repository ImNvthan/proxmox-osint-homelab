# Clés d'API

Le homelab est conçu pour être **utile sans aucune clé** (crt.sh, Shodan
InternetDB, GreyNoise community, iptoasn, ipinfo, Wayback, DuckDuckGo, OTX,
RapidDNS, HackerTarget, Anubis, `recherche-entreprises.api.gouv.fr`…).

> **Recherche par nom → réseaux sociaux :** sans clé, `osint person` interroge
> DuckDuckGo HTML, souvent **bloqué depuis un VPS/datacenter** → 0 résultat.
> Pour que « nom → LinkedIn/Twitter/Insta » marche de façon fiable, ajoutez
> `GOOGLE_CSE_KEY` + `GOOGLE_CSE_CX` (gratuit, 100 requêtes/jour) — voir ci-dessous.

## Google Programmable Search (recommandé, gratuit)

1. <https://programmablesearchengine.google.com/> → **Ajouter** un moteur →
   cochez **« Rechercher sur l'ensemble du Web »** → créez-le → copiez l'**ID du
   moteur de recherche** (`cx`).
2. <https://console.cloud.google.com/> → créez/choisissez un projet →
   **API et services → Bibliothèque →** activez **« Custom Search API »** →
   **Identifiants → Créer des identifiants → Clé API** → copiez-la.
3. Dans `/etc/osint/osint.env` :
   ```
   GOOGLE_CSE_KEY="AIza...."
   GOOGLE_CSE_CX="xxxxxxxxxxxxxxxxx"
   ```
4. `osint doctor` → la ligne `GOOGLE_CSE_KEY` doit passer ✔. Quota : 100/jour
   (au-delà : erreur 429, on retombe sur DuckDuckGo).

Ajouter des clés élargit la couverture. Éditez `/etc/osint/osint.env`
(`cp /opt/osint/src/tools/etc/osint.env.example /etc/osint/osint.env` s'il
manque), puis `osint doctor`.

| Variable | Fournisseur | Palier gratuit | Débloque |
|---|---|---|---|
| `GOOGLE_CSE_KEY` + `GOOGLE_CSE_CX` | Google Programmable Search | **100/jour** | recherche web fiable pour `osint person` / `relations` (profils LinkedIn, Twitter…) |
| `SERPAPI_KEY` | serpapi.com | 100/mois | idem, repli si pas de clé Google |
| `SHODAN_API_KEY` | shodan.io | avec compte | données d'hôte complètes (`osint ip`), SpiderFoot |
| `HIBP_API_KEY` | haveibeenpwned.com | payant | fuites dans `osint email` |
| `HUNTER_API_KEY` | hunter.io | 25/mois | vérification d'e-mail, e-mails d'un domaine |
| `GITHUB_TOKEN` | PAT github.com (sans scope) | oui | limites d'API relevées, gitleaks |
| `GREYNOISE_API_KEY` | greynoise.io | oui | GreyNoise authentifié |
| `SECURITYTRAILS_API_KEY` | securitytrails.com | 50/mois | plus de sous-domaines |
| `VIRUSTOTAL_API_KEY` | virustotal.com | 500/jour | DNS passif, sous-domaines |
| `CENSYS_API_ID` / `CENSYS_API_SECRET` | censys.io | oui | hôtes / certificats |
| `BINARYEDGE_API_KEY` | binaryedge.io | 250/mois | services exposés |
| `INTELX_API_KEY` | intelx.io | limité | index fuites / darknet |
| `DEHASHED_EMAIL` / `DEHASHED_KEY` | dehashed.com | payant | fuites pour h8mail |

## subfinder
Lit `~/.config/subfinder/provider-config.yaml` (utilisateur qui lance `osint`).
Voir <https://github.com/projectdiscovery/subfinder#post-installation-instructions>.

## GHunt
`osint email` appelle `ghunt` s'il est présent ; il faut au préalable y injecter
des cookies Google valides (`ghunt login`). Sans cela, l'étape est ignorée.

## SpiderFoot
Clés dans l'UI **Settings → module settings** ou `/opt/spiderfoot/spiderfoot.conf`.
Liste de fournisseurs propre à SpiderFoot, indépendante de ce tableau.

## Sécurité
- `osint.env` : `0600`, propriété root, dans `.gitignore`.
- `osint doctor` affiche seulement *quelles* clés sont définies, jamais la valeur.
