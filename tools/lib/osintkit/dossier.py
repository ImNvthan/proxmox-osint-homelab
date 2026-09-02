#!/usr/bin/env python3
"""Rendu de l'« affiche » (dossier une page) à partir de graph.json.

    python3 -m osintkit.dossier <case_dir>                 # dossier maître + un par personne
    python3 -m osintkit.dossier <case_dir> --person person:jean-dupont
    python3 -m osintkit.dossier <case_dir> --pdf           # + PDF via chromium headless

Sorties : <case_dir>/dossier.html  et  <case_dir>/entities/<slug>/dossier.html
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

from .graph import Graph, node_id
from .normalize import platform_from_host, split_name

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except Exception:
    Environment = None

TPL_DIR = os.path.join(os.path.dirname(__file__), "templates")


# --------------------------------------------------------------------------- #
def _neighbors(g: Graph, pid: str):
    idx = {n["id"]: n for n in g.data["nodes"]}
    social, emails, phones, addrs, orgs, photos, related = [], [], [], [], [], [], []
    for e in g.data["edges"]:
        other = None
        if e["src"] == pid:
            other = idx.get(e["dst"])
        elif e["dst"] == pid:
            other = idx.get(e["src"])
        if not other:
            continue
        k, a, c = other["kind"], other.get("attrs", {}), e.get("confidence", 0.4)
        if k == "account":
            lbl = other["label"]
            plat = a.get("platform") or (lbl.split("/")[0] if "/" in lbl else lbl)
            if plat and "." in plat and " " not in plat:
                plat = platform_from_host(plat) or plat.rsplit(".", 1)[0]
            social.append({"platform": plat,
                           "handle": a.get("handle") or "",
                           "url": a.get("url") or _guess_url(a, other["label"]),
                           "confidence": max(c, other["confidence"])})
        elif k == "email":
            emails.append({"value": other["label"], "confidence": max(c, other["confidence"])})
        elif k == "phone":
            phones.append({"value": other["label"], "meta": a, "confidence": max(c, other["confidence"])})
        elif k == "address":
            addrs.append({"value": other["label"], "confidence": max(c, other["confidence"])})
        elif k == "organization":
            orgs.append({"value": other["label"], "confidence": max(c, other["confidence"])})
        elif k == "photo":
            photos.append(a.get("url") or other["label"])
        elif k == "person" and e["rel"] in {"family_of", "related_to", "same_as", "member_of"}:
            related.append({"id": other["id"], "name": other["label"], "rel": e.get("subtype") or e["rel"],
                            "confidence": c})
    def dedup(xs, key):
        best: dict = {}
        for x in xs:
            kk = key(x)
            if kk not in best or x["confidence"] > best[kk]["confidence"]:
                best[kk] = x
        return sorted(best.values(), key=lambda y: -y["confidence"])

    return {
        "social": dedup(social, lambda x: (x["platform"], x["handle"])),
        "emails": dedup(emails, lambda x: x["value"]),
        "phones": dedup(phones, lambda x: x["value"]),
        "addresses": dedup(addrs, lambda x: x["value"].lower()),
        "orgs": dedup(orgs, lambda x: x["value"].lower()),
        "photos": list(dict.fromkeys(photos))[:4],
        "related": dedup(related, lambda x: x["id"]),
    }


def _guess_url(attrs: dict, label: str) -> str:
    plat = attrs.get("platform")
    handle = attrs.get("handle")
    if not (plat and handle):
        if "/" in label:
            plat, handle = label.split("/", 1)
    base = {
        "twitter": "https://x.com/", "instagram": "https://instagram.com/",
        "facebook": "https://facebook.com/", "linkedin": "https://linkedin.com/in/",
        "tiktok": "https://tiktok.com/@", "github": "https://github.com/",
        "gitlab": "https://gitlab.com/", "youtube": "https://youtube.com/@",
        "reddit": "https://reddit.com/user/", "telegram": "https://t.me/",
        "pinterest": "https://pinterest.com/", "snapchat": "https://snapchat.com/add/",
        "twitch": "https://twitch.tv/", "mastodon": "https://mastodon.social/@",
        "bluesky": "https://bsky.app/profile/", "threads": "https://threads.net/@",
    }.get(plat or "", "")
    return (base + handle) if base and handle else ""


def _person_dossier_ctx(g: Graph, node: dict) -> dict:
    a = node.get("attrs", {})
    is_person = node["kind"] == "person"
    first = a.get("first_name") or (split_name(node["label"])[0] if is_person else "")
    last = a.get("last_name") or (split_name(node["label"])[1] if is_person else "")
    nb = _neighbors(g, node["id"])
    runs = sorted({s for s in node["sources"] if s.startswith("run:")})
    tools = sorted({s for s in node["sources"] if not s.startswith(("run:", "seed"))})
    if is_person:
        display = f"{last.upper()} {first}".strip() if last else node["label"]
    else:
        display = f"Identité liée à {node['label']}"
        # le sélecteur-ancre lui-même figure dans la fiche
        if node["kind"] == "email":
            nb["emails"] = [{"value": node["label"], "confidence": node["confidence"]}] + nb["emails"]
        elif node["kind"] == "phone":
            nb["phones"] = [{"value": node["label"], "meta": a, "confidence": node["confidence"]}] + nb["phones"]
    return {
        "id": node["id"], "first_name": first, "last_name": last,
        "display": display, "confidence": node["confidence"],
        "birthdate": a.get("birthdate") or a.get("dob") or "",
        **nb, "runs": runs, "tools": tools,
    }


# --------------------------------------------------------------------------- #
def render(case_dir: str, only_person: str | None = None, pdf: bool = False) -> list[str]:
    g = Graph.load(case_dir)
    persons = [n for n in g.data["nodes"] if n["kind"] == "person"]
    if only_person:
        persons = [n for n in persons if n["id"] == only_person]
    # aucune personne consolidée -> fiche « identité liée à <sélecteur> »
    if not persons and not only_person:
        idx = {n["id"]: n for n in g.data["nodes"]}
        seed = g.data.get("seed") or {}
        seed_id = node_id(seed.get("kind", ""), seed.get("value", "")) if seed else ""
        hub = idx.get(seed_id)
        if hub is None:
            cand = [n for n in g.data["nodes"] if n["kind"] in ("email", "phone", "username")]
            hub = max(cand, key=lambda n: n["confidence"]) if cand else None
        if hub is not None:
            persons = [hub]
    persons.sort(key=lambda n: (-n["confidence"], n["label"]))

    ent_dir = os.path.join(case_dir, "entities")
    os.makedirs(ent_dir, exist_ok=True)
    written: list[str] = []

    people_ctx = [_person_dossier_ctx(g, p) for p in persons]
    # relie chaque « related » à son propre contexte pour l'imbrication d'affiche
    ctx_by_id = {c["id"]: c for c in people_ctx}
    for c in people_ctx:
        for r in c["related"]:
            r["ctx"] = ctx_by_id.get(r["id"])

    case_meta = {
        "case": g.data.get("case", os.path.basename(case_dir.rstrip("/"))),
        "seed": g.data.get("seed"),
        "created": g.data.get("created", ""),
        "updated": g.data.get("updated", ""),
        "n_nodes": len(g.data["nodes"]), "n_edges": len(g.data["edges"]),
    }

    env = _env()
    for c in people_ctx:
        slugd = c["id"].split(":", 1)[-1]
        d = os.path.join(ent_dir, slugd)
        os.makedirs(d, exist_ok=True)
        html = _render_one(env, "dossier.html.j2", {"p": c, "case": case_meta, "standalone": True})
        path = os.path.join(d, "dossier.html")
        _write(path, html)
        written.append(path)
        if pdf:
            _to_pdf(path)

    master = _render_one(env, "case.html.j2",
                         {"people": people_ctx, "case": case_meta,
                          "graph_available": os.path.exists(os.path.join(case_dir, "graph.svg"))})
    mpath = os.path.join(case_dir, "dossier.html")
    _write(mpath, master)
    written.append(mpath)
    if pdf:
        _to_pdf(mpath)
    return written


# --------------------------------------------------------------------------- #
def _env():
    if Environment is None or not os.path.isdir(TPL_DIR):
        return None
    return Environment(loader=FileSystemLoader(TPL_DIR),
                       autoescape=select_autoescape(["html", "j2"]),
                       trim_blocks=True, lstrip_blocks=True)


def _render_one(env, tpl_name: str, ctx: dict) -> str:
    if env is not None:
        try:
            return env.get_template(tpl_name).render(**ctx)
        except Exception as exc:  # pragma: no cover
            sys.stderr.write(f"[dossier] jinja: {exc}; repli texte\n")
    return _fallback(ctx)


def _fallback(ctx: dict) -> str:
    p = ctx.get("p")
    if not p:  # dossier maître
        rows = "".join(f"<li>{c['display']} — confiance {c['confidence']}</li>" for c in ctx.get("people", []))
        return f"<!doctype html><meta charset=utf-8><title>Dossier</title><h1>Enquête {ctx['case']['case']}</h1><ul>{rows}</ul>"
    def sec(title, items):
        return f"<h3>{title}</h3><ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"
    return ("<!doctype html><meta charset=utf-8><title>%s</title>"
            "<style>body{font:14px system-ui;margin:2rem;max-width:800px}</style>"
            "<h1>%s</h1>%s%s%s%s%s" % (
                p["display"], p["display"],
                sec("Téléphones", [x["value"] for x in p["phones"]]),
                sec("E-mails", [x["value"] for x in p["emails"]]),
                sec("Adresses", [x["value"] for x in p["addresses"]]),
                sec("Réseaux sociaux", [f"{x['platform']} {x['url']}" for x in p["social"]]),
                sec("Proches", [x["name"] for x in p["related"]]),
            ))


def _write(path: str, html: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)


def _to_pdf(html_path: str) -> str | None:
    pdf_path = html_path[:-5] + ".pdf"
    for exe in ("chromium", "chromium-browser", "google-chrome"):
        if shutil.which(exe):
            try:
                subprocess.run([exe, "--headless", "--no-sandbox", "--disable-gpu",
                                f"--print-to-pdf={pdf_path}", "--no-pdf-header-footer",
                                "file://" + os.path.abspath(html_path)],
                               check=True, timeout=90, capture_output=True)
                return pdf_path
            except Exception as exc:
                sys.stderr.write(f"[dossier] pdf via {exe}: {exc}\n")
                return None
    if shutil.which("weasyprint"):
        try:
            subprocess.run(["weasyprint", html_path, pdf_path], check=True, timeout=90, capture_output=True)
            return pdf_path
        except Exception:
            return None
    sys.stderr.write("[dossier] aucun moteur PDF (chromium/weasyprint) — HTML seulement\n")
    return None


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: python3 -m osintkit.dossier <case_dir> [--person ID] [--pdf]", file=sys.stderr)
        return 2
    case_dir = argv[0]
    person = argv[argv.index("--person") + 1] if "--person" in argv else None
    written = render(case_dir, person, "--pdf" in argv)
    for w in written:
        print(w)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
