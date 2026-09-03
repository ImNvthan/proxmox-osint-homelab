#!/usr/bin/env python3
"""Découverte de proches / famille à partir d'un nom (SOUS CONDITION).

Activé seulement si osint-recon-relations est appelé (lui-même protégé par
`OSINT_ALLOW_RELATIONS=1` ou `--relations`). N'utilise QUE des sources
publiques et des requêtes de moteurs de recherche — aucune authentification,
aucun contournement de CGU, aucun scraping massif.

    python3 -m osintkit.relations "Jean Dupont" --ville Lyon --pays FR --out relations.json

Sortie JSON : {query, dorks[], results[], relations[], profiles[]}
`relations[]` = candidats co-mentionnés avec un mot de parenté ou le même nom
de famille — confiance basse par construction, à valider humainement.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from urllib.parse import urlparse

from .extract import KIN_WORDS, NAME_RE
from .normalize import platform_from_host, split_name, strip_accents
from .websearch import search as _websearch  # Google CSE > SerpAPI > DuckDuckGo

try:
    import requests
except Exception:
    requests = None

UA = "Mozilla/5.0 (X11; Linux x86_64) osint-lxc/2.0 (+recherche autorisée uniquement)"
TIMEOUT = 20


def search(query: str, serpapi_key: str = "") -> list[dict]:
    return _websearch(query, serpapi_key,
                      os.environ.get("GOOGLE_CSE_KEY", ""),
                      os.environ.get("GOOGLE_CSE_CX", ""))


# --------------------------------------------------------------------------- #
def build_dorks(name: str, company: str = "", city: str = "") -> list[str]:
    q = f'"{name}"'
    c = f' "{city}"' if city else ""
    co = f' "{company}"' if company else ""
    return [
        f'{q}{c} (famille OR épouse OR mari OR fils OR fille OR parents OR "née")',
        f'{q} site:linkedin.com/in',
        f'{q}{co} (site:twitter.com OR site:x.com OR site:instagram.com OR site:facebook.com OR site:tiktok.com)',
        f'{q} site:copainsdavant.linternaute.com',
        f'{q}{c} (avis OR obsèques OR "avis de décès" OR hommage)',
        f'{q}{co} (dirigeant OR gérant OR président OR associé)',
        f'{q}{c} (adresse OR domicile OR "demeurant")',
        f'{q} (filetype:pdf OR filetype:docx)',
    ]


# --------------------------------------------------------------------------- #
def _annuaire_entreprises(name: str) -> list[dict]:
    """API open data annuaire-entreprises.data.gouv.fr — dirigeants homonymes."""
    if requests is None:
        return []
    try:
        r = requests.get("https://recherche-entreprises.api.gouv.fr/search",
                         params={"q": name, "page": 1, "per_page": 5,
                                 "type_personne": "dirigeant"},
                         headers={"User-Agent": UA}, timeout=TIMEOUT)
        j = r.json()
    except Exception:
        return []
    out = []
    for comp in j.get("results", []):
        for d in comp.get("dirigeants", []):
            nom = " ".join(x for x in (d.get("prenoms"), d.get("nom")) if x).strip()
            if nom:
                out.append({"name": nom.title(), "relation": "professionnel",
                            "via": comp.get("nom_complet", ""), "confidence": 0.35})
    return out


# --------------------------------------------------------------------------- #
def find_relations(name: str, city: str = "", company: str = "", country: str = "FR",
                   serpapi_key: str = "", max_queries: int = 6) -> dict:
    first, last = split_name(name)
    last_slug = strip_accents(last).lower()
    dorks = build_dorks(name, company, city)
    results: list[dict] = []
    for d in dorks[:max_queries]:
        results.extend({**h, "query": d} for h in search(d, serpapi_key))
        time.sleep(1.2)  # courtoisie

    relations: dict[str, dict] = {}
    profiles: set[str] = set()

    def consider(cand: str, why: str, conf: float):
        cand = re.sub(r"\s+", " ", cand).strip(" .,-")
        cf, cl = split_name(cand)
        if not cf or not cl or len(cand) > 45:
            return
        if strip_accents(cand).lower() == strip_accents(name).lower():
            return
        key = strip_accents(cand).lower()
        cur = relations.get(key)
        if cur is None or conf > cur["confidence"]:
            relations[key] = {"name": cand.title() if cand.islower() else cand,
                              "relation": why, "confidence": round(conf, 2)}

    for hit in results:
        blob = f"{hit.get('title','')} — {hit.get('snippet','')}"
        host = (urlparse(hit.get("url", "")).hostname or "").lower()
        if platform_from_host(host):
            profiles.add(hit["url"])
        low = strip_accents(blob).lower()
        near_kin = any(k in low for k in (strip_accents(w) for w in KIN_WORDS))
        for m in NAME_RE.finditer(blob):
            cand = f"{m.group(1)} {m.group(2)}".strip()
            cl = strip_accents(split_name(cand)[1]).lower()
            if cl and last_slug and cl == last_slug:
                consider(cand, "même nom de famille", 0.45 if not near_kin else 0.55)
            elif near_kin:
                # nom proche d'un mot de parenté dans le même extrait
                consider(cand, "co-mention (parenté)", 0.4)

    for d in _annuaire_entreprises(name):
        key = strip_accents(d["name"]).lower()
        if key not in relations:
            relations[key] = d

    return {
        "query": name, "city": city, "company": company, "country": country,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dorks": dorks,
        "results": results,
        "relations": sorted(relations.values(), key=lambda r: -r["confidence"]),
        "profiles": sorted(profiles),
        "disclaimer": ("Candidats non vérifiés déduits de mentions publiques. "
                       "Traiter comme des pistes, jamais comme des faits. "
                       "Base légale requise (RGPD) pour conserver des données sur des tiers."),
    }


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: python3 -m osintkit.relations \"Prénom Nom\" [--ville V] [--entreprise E] "
              "[--pays FR] [--serpapi KEY] [--out fichier.json]", file=sys.stderr)
        return 2
    name = argv[0]
    opt = {"--ville": "", "--entreprise": "", "--pays": "FR", "--serpapi": "", "--out": ""}
    for i, a in enumerate(argv):
        if a in opt and i + 1 < len(argv):
            opt[a] = argv[i + 1]
    data = find_relations(name, opt["--ville"], opt["--entreprise"], opt["--pays"], opt["--serpapi"])
    js = json.dumps(data, ensure_ascii=False, indent=2)
    if opt["--out"]:
        with open(opt["--out"], "w", encoding="utf-8") as fh:
            fh.write(js)
        sys.stderr.write(f"[relations] {len(data['relations'])} candidats -> {opt['--out']}\n")
    else:
        print(js)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
