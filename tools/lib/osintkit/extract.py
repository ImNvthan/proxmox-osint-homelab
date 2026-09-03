#!/usr/bin/env python3
"""Extraction de sélecteurs depuis le répertoire d'une exécution osint-recon-*.

    python3 -m osintkit.extract <run_dir>            # -> écrit <run_dir>/selectors.jsonl
    python3 -m osintkit.extract <run_dir> --stdout   # -> aussi sur stdout

Chaque ligne : {"kind","value","source","confidence","url"?,"attrs"?}
kinds : email · phone · username · person_name · account · address · organization
        · domain · ip · photo · url
Tout est « au mieux » : un parseur qui échoue est ignoré, jamais fatal.
"""
from __future__ import annotations

import json
import os
import re
import sys

from .normalize import norm_email, norm_phone, platform_from_url

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,24}")
PHONE_RE = re.compile(r"\+\d[\d .()\-]{7,16}\d")
URL_RE = re.compile(r"https?://[^\s\"'<>)\]}]+")
HANDLE_RE = re.compile(r"(?<![\w@/.])@([A-Za-z0-9_]{3,30})\b")
KIN_WORDS = ("père", "mère", "fils", "fille", "épouse", "epoux", "époux", "mari",
             "femme", "frère", "soeur", "sœur", "conjoint", "conjointe", "compagne",
             "compagnon", "veuve", "veuf", "née", "nee", "parents", "famille",
             "beau-frère", "belle-soeur", "grand-père", "grand-mère", "petit-fils",
             "petite-fille", "oncle", "tante", "cousin", "cousine", "neveu", "nièce")
NAME_RE = re.compile(r"\b([A-ZÉÈÀÂÊÎÔÛÄ][a-zéèàâêîôûäëïöü'’\-]{1,20})\s"
                     r"([A-ZÉÈÀÂÊÎÔÛÄ][A-ZÉÈÀ a-zéèàâêîôûäëïöü'’\-]{1,30})")

DROP_EMAIL_DOMAINS = ("example.com", "sentry.io", "wixpress.com", "domain.com",
                      "email.com", "test.com", "your-domain.com")


def _sel(kind, value, source, confidence, **extra):
    d = {"kind": kind, "value": value, "source": source, "confidence": round(float(confidence), 3)}
    d.update({k: v for k, v in extra.items() if v})
    return d


def _read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except Exception:
        return ""


def _json(path):
    txt = _read(path)
    if not txt.strip():
        return None
    try:
        return json.loads(txt)
    except Exception:
        # jsonl -> liste
        out = []
        for line in txt.splitlines():
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
        return out or None


# --------------------------------------------------------------------------- #
def extract(run_dir: str, region: str = "FR") -> list[dict]:
    raw = os.path.join(run_dir, "raw")
    meta = _parse_env(os.path.join(run_dir, "meta.env"))
    rtype, target = meta.get("type", ""), meta.get("target", "")
    out: list[dict] = []
    seen: set[tuple] = set()

    def push(s):
        if not s["value"]:
            return
        key = (s["kind"], s["value"].lower())
        if key in seen:                       # enrichir l'entrée existante
            for e in out:
                if (e["kind"], e["value"].lower()) == key:
                    if s.get("attrs"):
                        e.setdefault("attrs", {}).update(s["attrs"])
                    if s.get("url") and not e.get("url"):
                        e["url"] = s["url"]
                    e["confidence"] = max(e["confidence"], s["confidence"])
                    break
            return
        seen.add(key)
        out.append(s)

    # la cible elle-même est un sélecteur confirmé
    if rtype in {"email", "phone", "username", "domain", "ip"} and target:
        push(_sel(rtype, target, "cible", 1.0))
    if rtype == "person" and target:
        push(_sel("person_name", target, "cible", 1.0))

    P = lambda name: os.path.join(raw, name)  # noqa: E731

    # ---- holehe : services où l'e-mail est inscrit ----------------------
    for txt in (_read(P("holehe.txt")),):
        for line in txt.splitlines():
            m = re.match(r"\s*\[\+\]\s+([A-Za-z0-9.\-]+\.[A-Za-z]{2,})", line)
            if m:
                push(_sel("account", m.group(1).lower(), "holehe", 0.8))

    # ---- sherlock : un fichier par pseudo, lignes = URLs ---------------
    sd = P("sherlock_d")
    if os.path.isdir(sd):
        for f in os.listdir(sd):
            for u in URL_RE.findall(_read(os.path.join(sd, f))):
                plat, handle = platform_from_url(u)
                push(_sel("account", f"{plat}/{handle}" if plat and handle else u,
                          "sherlock", 0.75, url=u))
    for u in URL_RE.findall(_read(P("sherlock.txt"))):
        plat, handle = platform_from_url(u)
        push(_sel("account", f"{plat}/{handle}" if plat and handle else u, "sherlock", 0.75, url=u))

    # ---- maigret : JSON riche (fullname, gaia, location, image) --------
    md = P("maigret_d")
    maig_files = []
    if os.path.isdir(md):
        maig_files = [os.path.join(md, f) for f in os.listdir(md) if f.endswith(".json")]
    maig_files.append(P("maigret.txt"))
    for mf in maig_files:
        data = _json(mf)
        if not isinstance(data, dict):
            continue
        for site, info in data.items():
            if not isinstance(info, dict):
                continue
            st = info.get("status")
            status = str((st.get("status") if isinstance(st, dict) else st) or "").lower()
            url = info.get("url_user") or info.get("url")
            if status == "claimed" and url:
                plat, handle = platform_from_url(url)
                push(_sel("account", f"{plat}/{handle}" if plat and handle else url,
                          "maigret", 0.8, url=url))
            ids = (st.get("ids") if isinstance(st, dict) else None) or info.get("ids") or {}
            for key, vals in (ids.items() if isinstance(ids, dict) else []):
                vals = vals if isinstance(vals, list) else [vals]
                for v in vals:
                    v = str(v).strip()
                    if not v:
                        continue
                    kl = key.lower()
                    if "name" in kl or kl in {"fullname", "full_name"}:
                        if " " in v:
                            push(_sel("person_name", v, "maigret", 0.55))
                    elif "email" in kl and EMAIL_RE.fullmatch(v):
                        push(_sel("email", norm_email(v), "maigret", 0.6))
                    elif "phone" in kl:
                        e164 = norm_phone(v, region)[0]
                        if e164:
                            push(_sel("phone", e164, "maigret", 0.55))
                    elif "location" in kl or "city" in kl or "address" in kl:
                        push(_sel("address", v, "maigret", 0.4))
                    elif "image" in kl or "avatar" in kl or "photo" in kl:
                        if v.startswith("http"):
                            push(_sel("photo", v, "maigret", 0.5, url=v))

    # ---- socialscan : pseudo/e-mail pris sur des plateformes ----------
    ss = _json(P("socialscan.json"))
    for item in (ss if isinstance(ss, list) else (ss or {}).get("results", []) if isinstance(ss, dict) else []):
        if isinstance(item, dict) and item.get("available") is False and item.get("platform"):
            push(_sel("account", str(item["platform"]).lower(), "socialscan", 0.55))

    # ---- github / gitlab / gravatar --------------------------------
    gh = _json(P("github.json"))
    if isinstance(gh, dict) and gh.get("login"):
        push(_sel("account", f"github/{gh['login']}", "github", 0.9, url=gh.get("html_url")))
        if gh.get("name") and " " in gh["name"]:
            push(_sel("person_name", gh["name"], "github", 0.6))
        if gh.get("email") and EMAIL_RE.fullmatch(gh["email"] or ""):
            push(_sel("email", norm_email(gh["email"]), "github", 0.7))
        if gh.get("twitter_username"):
            push(_sel("account", f"twitter/{gh['twitter_username']}", "github", 0.7))
        if gh.get("company"):
            push(_sel("organization", gh["company"].lstrip("@"), "github", 0.6))
        if gh.get("location"):
            push(_sel("address", gh["location"], "github", 0.45))
        if gh.get("blog"):
            push(_sel("url", gh["blog"], "github", 0.5, url=gh["blog"]))
        if gh.get("avatar_url"):
            push(_sel("photo", gh["avatar_url"], "github", 0.5, url=gh["avatar_url"]))
    grav = _json(P("gravatar.json")) or _json(P("gravatar.txt"))
    entries = (grav or {}).get("entry", []) if isinstance(grav, dict) else []
    for e in entries:
        if e.get("displayName") and " " in e["displayName"]:
            push(_sel("person_name", e["displayName"], "gravatar", 0.55))
        for acc in e.get("accounts", []) or []:
            if acc.get("url"):
                plat, handle = platform_from_url(acc["url"])
                push(_sel("account", f"{plat}/{handle}" if plat and handle else acc["url"],
                          "gravatar", 0.55, url=acc["url"]))
        if e.get("thumbnailUrl"):
            push(_sel("photo", e["thumbnailUrl"], "gravatar", 0.5, url=e["thumbnailUrl"]))

    # ---- phoneinfoga : porteur possible, empreintes ----------------
    pj = _json(P("phoneinfoga.json"))
    pt = _read(P("phoneinfoga.txt"))
    if isinstance(pj, dict):
        for res in (pj.get("results") or {}).values() if isinstance(pj.get("results"), dict) else []:
            for u in URL_RE.findall(json.dumps(res)):
                push(_sel("url", u, "phoneinfoga", 0.35, url=u))
    for u in URL_RE.findall(pt):
        if any(k in u for k in ("facebook.com", "google.com/search", "whitepages", "truecaller")):
            push(_sel("url", u, "phoneinfoga", 0.3, url=u))

    # ---- theHarvester : e-mails / hôtes / personnes ----------------
    for thf in (P("theharvester.json"),) + tuple(
            os.path.join(raw, f) for f in os.listdir(raw) if f.startswith("theharvester") and f.endswith(".json")) if os.path.isdir(raw) else ():
        th = _json(thf)
        if not isinstance(th, dict):
            continue
        for em in th.get("emails", []) or []:
            if EMAIL_RE.fullmatch(em or ""):
                push(_sel("email", norm_email(em), "theHarvester", 0.55))
        for host in th.get("hosts", []) or []:
            h = re.sub(r":.*$", "", str(host)).strip()
            if h:
                push(_sel("domain", h.lower(), "theHarvester", 0.4))
        for person in th.get("people", []) or th.get("linkedin_people", []) or []:
            person = re.sub(r"\s*-\s*.*$", "", str(person)).strip()
            if " " in person:
                push(_sel("person_name", person, "theHarvester", 0.45))

    # ---- relations (osint-recon-relations) : candidats famille -----
    rel = _json(P("relations.json"))
    if isinstance(rel, dict):
        for cand in rel.get("relations", []):
            nm = cand.get("name")
            if nm and " " in nm:
                push(_sel("person_name", nm, f"relations:{cand.get('relation','proche')}",
                          float(cand.get("confidence", 0.35))))
        for u in rel.get("profiles", []):
            plat, handle = platform_from_url(u)
            push(_sel("account", f"{plat}/{handle}" if plat and handle else u, "relations", 0.4, url=u))

    # ---- websearch (osint-recon-person) : profils sociaux du NOM --
    ws = _json(P("websearch.json"))
    if isinstance(ws, dict):
        for pr in ws.get("profiles", []):
            plat, url = pr.get("platform"), pr.get("url")
            _p2, handle = platform_from_url(url) if url else (None, None)
            key = f"{plat}/{handle}" if plat and handle else (plat or url)
            if key:
                push(_sel("account", key, "websearch", 0.62, url=url))
        for em in ws.get("emails", []):
            if EMAIL_RE.fullmatch(em or "") and em.split("@")[-1] not in DROP_EMAIL_DOMAINS:
                push(_sel("email", norm_email(em), "websearch", 0.55))
        for ph in ws.get("phones", []):
            e164, meta = norm_phone(ph, region)
            if e164:
                push(_sel("phone", e164, "websearch", 0.5))

    # ---- phone-parse (python-phonenumbers) : opérateur / type / région
    pp = _json(P("phone-parse.json"))
    if isinstance(pp, dict) and pp.get("e164"):
        attrs = {k: pp[k] for k in ("carrier", "type", "region", "valid") if pp.get(k)}
        push(_sel("phone", pp["e164"], "phonenumbers", 0.95, attrs=attrs))
        if pp.get("region"):
            push(_sel("address", str(pp["region"]), "phonenumbers", 0.3))

    # ---- person : promeut quelques pseudos candidats pour le pivot -
    if rtype == "person":
        cand = [u.strip() for u in _read(P("usernames.txt")).splitlines() if u.strip()]
        for u in cand[:5]:
            push(_sel("username", u, "permutation", 0.58))
        for e in [x.strip() for x in _read(P("emails.txt")).splitlines() if x.strip()][:6]:
            if EMAIL_RE.fullmatch(e):
                push(_sel("email", norm_email(e), "permutation", 0.35))

    # ---- whois (domain/ip) : titulaire ---------------------------
    who = _read(P("whois.txt"))
    if who:
        m = re.search(r"(?:Registrant Organization|org-name|OrgName):\s*(.+)", who, re.I)
        if m and "redacted" not in m.group(1).lower() and "privacy" not in m.group(1).lower():
            push(_sel("organization", m.group(1).strip(), "whois", 0.6))
        m = re.search(r"(?:Registrant Name):\s*(.+)", who, re.I)
        if m and "redacted" not in m.group(1).lower() and " " in m.group(1):
            push(_sel("person_name", m.group(1).strip(), "whois", 0.45))

    # ---- balayage générique de tout raw/*.{txt,json,jsonl} -------
    # (on exclut les fichiers de PERMUTATIONS synthétiques : ce sont des
    #  devinettes, pas des trouvailles — elles pollueraient le graphe/dossier)
    SYNTH = {"emails.txt", "usernames.txt", "permutations.json", "dorks.md",
             "dorks-phone.md", "candidate-emails.txt", "websearch.json"}
    for fn in sorted(os.listdir(raw)) if os.path.isdir(raw) else []:
        if not fn.endswith((".txt", ".json", ".jsonl", ".md")) or fn in SYNTH:
            continue
        blob = _read(os.path.join(raw, fn))
        if len(blob) > 400_000:
            blob = blob[:400_000]
        for em in EMAIL_RE.findall(blob):
            em = norm_email(em)
            if em.split("@")[-1] not in DROP_EMAIL_DOMAINS and not em.endswith((".png", ".jpg")):
                push(_sel("email", em, f"regex:{fn}", 0.4))
        for ph in PHONE_RE.findall(blob):
            e164, meta = norm_phone(ph, region)
            if e164 and meta.get("valid"):
                push(_sel("phone", e164, f"regex:{fn}", 0.4))
        for u in URL_RE.findall(blob):
            plat, handle = platform_from_url(u)
            if plat and handle and handle.lower() not in {"share", "intent", "home", "login"}:
                push(_sel("account", f"{plat}/{handle}", f"regex:{fn}", 0.45, url=u))

    return out


def _parse_env(path: str) -> dict:
    d: dict = {}
    for line in _read(path).splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            v = v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
                v = v[1:-1]
            elif "\\" in v:                       # déséchappe la sortie de printf %q
                v = re.sub(r"\\(.)", r"\1", v)
            d[k.strip()] = v
    return d


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: python3 -m osintkit.extract <run_dir> [--stdout] [--region FR]", file=sys.stderr)
        return 2
    run_dir = argv[0]
    region = "FR"
    if "--region" in argv:
        region = argv[argv.index("--region") + 1]
    sels = extract(run_dir, region)
    out_path = os.path.join(run_dir, "selectors.jsonl")
    with open(out_path, "w", encoding="utf-8") as fh:
        for s in sels:
            fh.write(json.dumps(s, ensure_ascii=False) + "\n")
    if "--stdout" in argv:
        for s in sels:
            print(json.dumps(s, ensure_ascii=False))
    sys.stderr.write(f"[extract] {len(sels)} sélecteurs -> {out_path}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
