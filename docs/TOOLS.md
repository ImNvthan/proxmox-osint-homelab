# Inventaire des outils

Installé par `install/osint-install.sh`. Ce qui manque est consigné dans
`/opt/osint/install-warnings.log` — `osint doctor` donne l'état en direct
(binaires **et** modules python du moteur).

## Moteur d'autopilote (python)
| Composant | Rôle | Paquet |
|---|---|---|
| osintkit.classify | détection du type d'un sélecteur | (stdlib) |
| osintkit.normalize | E.164, e-mails, pseudos, URL→plateforme, noms | `python3-phonenumbers` |
| osintkit.extract | sortie brute d'un outil → sélecteurs normalisés | (stdlib) |
| osintkit.graph | graphe d'entités `graph.json`, fusion, rendu | `graphviz` |
| osintkit.relations | proches/famille (recherche web + open data) | `python3-requests`, `python3-bs4` |
| osintkit.dossier | affiche HTML/PDF | `python3-jinja2`, `chromium` |
| osintkit.web | interface de saisie | `python3-flask` |

## Personnes / comptes
| Outil | Rôle | Utilisé par |
|---|---|---|
| sherlock | pseudo sur ~400 sites | `username` |
| maigret | pseudo + analyse de profils (JSON riche : nom, image, localisation) | `username` |
| blackbird | pseudo/e-mail sur de nombreux sites (JSON) | `username` |
| socialscan | disponibilité e-mail/pseudo sur les grandes plateformes | `username`, `email` |
| holehe | sites où une adresse e-mail est inscrite | `email` |
| h8mail | recherche de fuites (local + fournisseurs avec clé) | `email` |
| ghunt | compte Google (cookies requis) | `email`, manuel |
| toutatis | données d'un compte Instagram | manuel |
| xeuledoc | métadonnées de Google Docs publics | manuel |
| ignorant | inscription par numéro de téléphone | `phone` |
| phoneinfoga | reconnaissance sur numéro | `phone` |
| python-phonenumbers | parse E.164 : opérateur, type, région | `phone` |

## Reconnaissance domaine / infra
| Outil | Rôle |
|---|---|
| subfinder · assetfinder · amass (passif) · crt.sh | énumération de sous-domaines |
| dnsx · dnsrecon · dig | résolution / enregistrements DNS |
| httpx | sondage HTTP (statut, titre, techno, TLS) |
| gowitness | captures d'écran headless |
| gau · waymore | URLs historiques (Wayback / CommonCrawl / OTX) |
| whatweb | empreinte technologique (passif `-a 1`) |
| dnstwist | typosquatting / domaines sosies |
| checkdmarc | SPF / DKIM / DMARC / MX / BIMI |
| theHarvester | e-mails, hôtes, personnes (sources sans clé) |
| Shodan InternetDB | ports / CVE / noms d'hôtes par IP (sans clé) |

## IP / réseau
whois · iptoasn (ASN) · ipinfo (géo) · DNS inverse · Shodan InternetDB ·
GreyNoise community · (nmap/masscan seulement avec `--active`).

## Plateforme & annexe
| Outil | Rôle |
|---|---|
| SpiderFoot | automatisation corrélée complète (systemd, 127.0.0.1:5001) |
| recon-ng | cadre de reconnaissance modulaire |
| Tor + torsocks + proxychains4 | sortie anonymisée : `torsocks osint …` |
| exiftool / mediainfo / tesseract / poppler | métadonnées fichiers/images, OCR |
| gitleaks | secrets dans des dépôts clonés |
| graphviz (`dot`) | rendu du graphe d'entités |
| pandoc / weasyprint / chromium | rendu des rapports et affiches |

## Listes de mots
`/opt/osint/wordlists/` — top 5000 sous-domaines SecLists (récupéré à l'installation).
