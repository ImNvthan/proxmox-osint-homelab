# Clés d'API

Le homelab est conçu pour être **utile sans aucune clé** (crt.sh, Shodan
InternetDB, GreyNoise community, iptoasn, ipinfo, Wayback, DuckDuckGo, OTX,
RapidDNS, HackerTarget, Anubis, `recherche-entreprises.api.gouv.fr`…).

Ajouter des clés élargit la couverture. Éditez `/etc/osint/osint.env`
(`cp /opt/osint/src/tools/etc/osint.env.example /etc/osint/osint.env` s'il
manque), puis `osint doctor`.

| Variable | Fournisseur | Palier gratuit | Débloque |
|---|---|---|---|
| `SERPAPI_KEY` | serpapi.com | 100/mois | recherche web fiable pour `osint relations` (sinon DuckDuckGo HTML) |
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
