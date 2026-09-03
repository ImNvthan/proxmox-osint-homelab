#!/usr/bin/env python3
"""Recherche web SANS clé (DuckDuckGo HTML) + extraction de profils / e-mails.

Utilisé par osint-recon-person (cible principale) et osint-recon-relations
(entourage). Uniquement des requêtes de moteur de recherche publiques — aucune
authentification, aucun contournement de CGU.

    python3 -m osintkit.websearch person "Prénom Nom" --ville Lyon --out websearch.json
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from urllib.parse import urlparse

try:
    import requests
except Exception:
    requests = None

from .normalize import platform_from_host

UA = ("Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0")
TIMEOUT = 20
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,24}")
PHONE_RE = re.compile(r"(?:\+33|0)\s?[1-9](?:[\s.\-]?\d{2}){4}")


def _ddg(query: str) -> list[dict]:
    if requests is None:
        return []
    try:
        r = requests.post("https://html.duckduckgo.com/html/", data={"q": query, "kl": "fr-fr"},
                          headers={"User-Agent": UA}, timeout=TIMEOUT)
        r.raise_for_status()
    except Exception:
        return []
    page = r.text
    anchors = re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', page, re.S)
    snips = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', page, re.S)
    out = []
    for i, (href, title_html) in enumerate(anchors[:20]):
        url = re.sub(r"^.*?[?&]uddg=", "", href)
        try:
            url = requests.utils.unquote(url)
        except Exception:
            pass
        url = url.split("&rut=")[0]
        if not url.startswith("http"):
            continue
        out.append({
            "title": re.sub(r"<[^>]+>", "", title_html or "").strip(),
            "url": url,
            "snippet": re.sub(r"<[^>]+>", "", snips[i] if i < len(snips) else "").strip(),
        })
    return out


def _serpapi(query: str, key: str) -> list[dict]:
    if requests is None:
        return []
    try:
        r = requests.get("https://serpapi.com/search.json",
                         params={"q": query, "api_key": key, "hl": "fr", "num": 20}, timeout=TIMEOUT)
        j = r.json()
    except Exception:
        return []
    return [{"title": it.get("title", ""), "url": it.get("link", ""), "snippet": it.get("snippet", "")}
            for it in j.get("organic_results", [])]


def _google_cse(query: str, key: str, cx: str) -> list[dict]:
    """Google Programmable Search — 100 requêtes/jour gratuites."""
    if requests is None or not (key and cx):
        return []
    try:
        r = requests.get("https://www.googleapis.com/customsearch/v1",
                         params={"key": key, "cx": cx, "q": query, "num": 10, "hl": "fr"},
                         timeout=TIMEOUT)
        j = r.json()
    except Exception:
        return []
    return [{"title": it.get("title", ""), "url": it.get("link", ""), "snippet": it.get("snippet", "")}
            for it in j.get("items", [])]


def search(query: str, serpapi_key: str = "", google_key: str = "", google_cx: str = "") -> list[dict]:
    # priorité : Google CSE (100/j) > SerpAPI (100/mois) > DuckDuckGo (sans clé)
    if google_key and google_cx:
        res = _google_cse(query, google_key, google_cx)
        if res:
            return res
    if serpapi_key:
        res = _serpapi(query, serpapi_key)
        if res:
            return res
    return _ddg(query)


def person_dorks(name: str, city: str = "", company: str = "") -> list[str]:
    q = f'"{name}"'
    c = f' "{city}"' if city else ""
    co = f' "{company}"' if company else ""
    return [
        f'{q} site:linkedin.com/in',
        f'{q}{co} (site:twitter.com OR site:x.com OR site:instagram.com OR site:facebook.com OR site:tiktok.com)',
        f'{q} (site:github.com OR site:gitlab.com OR site:keybase.io OR site:medium.com)',
        f'{q}{c} (site:viadeo.com OR site:copainsdavant.linternaute.com OR site:trombi.com OR site:pagesjaunes.fr)',
        f'{q}{co}{c}',
        f'{q}{co} (email OR "e-mail" OR contact OR "@")',
    ]


def search_person(name: str, city: str = "", company: str = "", serpapi_key: str = "",
                  google_key: str = "", google_cx: str = "",
                  max_queries: int = 6, pause: float = 1.4) -> dict:
    dorks = person_dorks(name, city, company)
    results: list[dict] = []
    for d in dorks[:max_queries]:
        for hit in search(d, serpapi_key, google_key, google_cx):
            results.append({**hit, "query": d})
        time.sleep(pause)

    profiles: dict[str, dict] = {}
    emails: set[str] = set()
    phones: set[str] = set()
    for hit in results:
        blob = f"{hit.get('title','')} {hit.get('snippet','')} {hit.get('url','')}"
        for em in EMAIL_RE.findall(blob):
            em = em.lower()
            if not em.endswith((".png", ".jpg", ".gif", ".webp")) and "sentry" not in em:
                emails.add(em)
        for ph in PHONE_RE.findall(blob):
            phones.add(ph.strip())
        u = hit.get("url", "")
        host = (urlparse(u).hostname or "").lower()
        plat = platform_from_host(host)
        if plat:
            key = u.split("?")[0].rstrip("/")
            if key not in profiles:
                profiles[key] = {"platform": plat, "url": key,
                                 "title": hit.get("title", ""), "query": hit.get("query", "")}

    return {
        "query": name, "city": city, "company": company,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dorks": dorks,
        "results": results,
        "profiles": list(profiles.values()),
        "emails": sorted(emails),
        "phones": sorted(phones),
    }


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] != "person":
        print('usage: python3 -m osintkit.websearch person "Prénom Nom" '
              '[--ville V] [--entreprise E] [--serpapi K] [--out f.json]', file=sys.stderr)
        return 2
    name = argv[1]
    opt = {"--ville": "", "--entreprise": "", "--serpapi": "", "--out": ""}
    for i, a in enumerate(argv):
        if a in opt and i + 1 < len(argv):
            opt[a] = argv[i + 1]
    data = search_person(
        name, opt["--ville"], opt["--entreprise"],
        serpapi_key=opt["--serpapi"] or os.environ.get("SERPAPI_KEY", ""),
        google_key=os.environ.get("GOOGLE_CSE_KEY", ""),
        google_cx=os.environ.get("GOOGLE_CSE_CX", ""),
    )
    js = json.dumps(data, ensure_ascii=False, indent=2)
    if opt["--out"]:
        with open(opt["--out"], "w", encoding="utf-8") as fh:
            fh.write(js)
        sys.stderr.write(f"[websearch] {len(data['profiles'])} profils, {len(data['emails'])} e-mails "
                         f"-> {opt['--out']}\n")
    else:
        print(js)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
