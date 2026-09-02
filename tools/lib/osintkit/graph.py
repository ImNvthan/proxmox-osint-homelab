#!/usr/bin/env python3
"""Graphe d'entités d'une enquête : personnes, e-mails, téléphones, comptes…

Fichier canonique : <case>/graph.json  (sans dépendance ; networkx/graphviz
seulement pour le rendu visuel, facultatif).

    python3 -m osintkit.graph merge  <case_dir> <selectors.jsonl> [--run NOM] [--anchor ID]
    python3 -m osintkit.graph render <case_dir>
    python3 -m osintkit.graph show   <case_dir>
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field

from .normalize import platform_from_url, slug, split_name

KINDS = {"person", "email", "phone", "username", "account", "address",
         "organization", "domain", "ip", "url", "photo"}

REL = {"owns", "uses", "same_as", "member_of", "works_at", "related_to",
       "family_of", "mentions", "resolves_to", "seed"}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def node_id(kind: str, value: str) -> str:
    if kind == "person":
        return "person:" + slug(value)
    if kind == "account":
        return "account:" + value.lower().strip("/")
    return f"{kind}:{value.strip().lower()}"


@dataclass
class Graph:
    path: str
    data: dict = field(default_factory=dict)

    # ---- io -------------------------------------------------------------
    @classmethod
    def load(cls, case_dir: str) -> "Graph":
        p = os.path.join(case_dir, "graph.json")
        g = cls(path=p)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                g.data = json.load(fh)
        else:
            g.data = {"case": os.path.basename(case_dir.rstrip("/")),
                      "created": _now(), "seed": None, "nodes": [], "edges": []}
        g.data.setdefault("nodes", [])
        g.data.setdefault("edges", [])
        return g

    def save(self) -> None:
        self.data["updated"] = _now()
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, ensure_ascii=False, indent=2, sort_keys=False)
        os.replace(tmp, self.path)

    # ---- accès --------------------------------------------------------
    def _index(self) -> dict:
        return {n["id"]: n for n in self.data["nodes"]}

    def get(self, nid: str) -> dict | None:
        return self._index().get(nid)

    def nodes_of(self, kind: str) -> list[dict]:
        return [n for n in self.data["nodes"] if n["kind"] == kind]

    # ---- mutation ---------------------------------------------------
    def upsert_node(self, kind: str, value: str, *, label: str | None = None,
                    attrs: dict | None = None, sources: list[str] | None = None,
                    confidence: float = 0.5) -> str:
        if kind not in KINDS:
            kind = "url"
        nid = node_id(kind, value)
        idx = self._index()
        n = idx.get(nid)
        if n is None:
            n = {"id": nid, "kind": kind, "label": label or value,
                 "attrs": {}, "sources": [], "confidence": 0.0, "first_seen": _now()}
            self.data["nodes"].append(n)
        if label and (n["label"] == n["id"].split(":", 1)[-1] or len(label) > len(n["label"])):
            n["label"] = label
        for s in sources or []:
            if s and s not in n["sources"]:
                n["sources"].append(s)
        n["confidence"] = round(max(n["confidence"], float(confidence)), 3)
        _merge_attrs(n["attrs"], attrs or {})
        return nid

    def add_edge(self, src: str, dst: str, rel: str, *, confidence: float = 0.5,
                 sources: list[str] | None = None, subtype: str | None = None) -> None:
        if src == dst:
            return
        for e in self.data["edges"]:
            if e["src"] == src and e["dst"] == dst and e["rel"] == rel:
                e["confidence"] = round(max(e["confidence"], float(confidence)), 3)
                for s in sources or []:
                    if s and s not in e["sources"]:
                        e["sources"].append(s)
                if subtype:
                    e["subtype"] = subtype
                return
        self.data["edges"].append({"src": src, "dst": dst, "rel": rel if rel in REL else "related_to",
                                   "confidence": round(float(confidence), 3),
                                   "sources": list(sources or []),
                                   **({"subtype": subtype} if subtype else {})})

    def set_seed(self, kind: str, value: str) -> str:
        self.data["seed"] = {"kind": kind, "value": value}
        return self.upsert_node(kind, value, sources=["seed"], confidence=1.0)

    # ---- fusion d'un lot de sélecteurs -----------------------------
    def merge_selectors(self, selectors: list[dict], *, run: str | None = None,
                        anchor: str | None = None) -> list[dict]:
        """Fusionne un lot de sélecteurs dans le graphe.

        `anchor` = id du nœud recherché (person:… ou email:… / phone:… / username:…).
        Tout ce qui est découvert est rattaché à l'ancre ; si un nom de personne
        apparaît, il devient le pivot (hub) et l'ancre non-personne lui est reliée
        par owns/uses. Retourne les nouveaux nœuds.
        """
        src_tag = f"run:{run}" if run else "extract"
        before = set(self._index())
        anchor_id = anchor or None
        anchor_kind = anchor_id.split(":", 1)[0] if anchor_id else None
        anchor_is_person = anchor_kind == "person"
        made: list[tuple[str, str, list[str], float]] = []  # (kind, nid, srcs, conf)

        for sel in selectors:
            kind = sel.get("kind")
            val = (sel.get("value") or "").strip()
            if not val or kind not in KINDS and kind not in {"person_name"}:
                continue
            conf = float(sel.get("confidence", 0.5))
            tool = sel.get("source") or ""
            srcs = [s for s in (src_tag, tool) if s]

            if kind == "person_name":
                pid = self.upsert_node("person", val, label=_person_label(val),
                                       attrs=_name_attrs(val), sources=srcs, confidence=conf)
                made.append(("person", pid, srcs, conf))
                continue

            if kind == "account":
                if "://" in val or ("." in val and "/" in val):
                    plat, handle = platform_from_url(val)
                elif "/" in val:                       # "twitter/jdupont"
                    p0, _, h = val.partition("/")
                    plat, handle = (p0 or None), (h or None)
                elif "." in val:                        # "instagram.com" (holehe)
                    plat, handle = platform_from_url(val)
                else:                                    # "instagram"
                    plat, handle = (val or None), None
                lbl = f"{plat}/{handle}" if plat and handle else (plat or val)
                key = f"{plat}/{handle}" if plat and handle else (plat or val)
                nid = self.upsert_node("account", key, label=lbl,
                                       attrs={"platform": plat, "handle": handle, "url": sel.get("url")},
                                       sources=srcs, confidence=conf)
            else:
                nid = self.upsert_node(kind, val, attrs=sel.get("attrs") or {}, sources=srcs, confidence=conf)
            made.append((kind, nid, srcs, conf))

        # pivot : une personne devient le hub (découverte dans ce lot, ou déjà
        # reliée à l'ancre lors d'une exécution précédente)
        new_persons = [nid for (k, nid, _s, _c) in made if k == "person"]
        hub = anchor_id if anchor_is_person else (new_persons[0] if len(new_persons) == 1 else None)
        if hub is None and anchor_id and not anchor_is_person:
            linked_persons = {
                (e["src"] if e["dst"] == anchor_id else e["dst"])
                for e in self.data["edges"]
                if anchor_id in (e["src"], e["dst"])
            }
            linked_persons = [p for p in linked_persons if p.startswith("person:")]
            if len(linked_persons) == 1:
                hub = linked_persons[0]

        sem = {"email": "owns", "phone": "owns", "username": "uses", "account": "uses",
               "address": "related_to", "organization": "works_at", "photo": "related_to"}

        for kind, nid, srcs, conf in made:
            if nid == hub:
                continue
            if kind == "person":
                # relie les personnes entre elles / à l'ancre
                if anchor_id and anchor_id != nid:
                    rel = "same_as" if anchor_is_person else "related_to"
                    self.add_edge(anchor_id, nid, rel, confidence=min(conf, 0.6), sources=srcs)
                continue
            if hub:
                self.add_edge(hub, nid, sem.get(kind, "related_to"),
                              confidence=min(conf, 0.9), sources=srcs)
            if anchor_id and anchor_id != nid and anchor_id != hub:
                self.add_edge(anchor_id, nid, "related_to", confidence=min(conf, 0.7), sources=srcs)

        # la personne-hub possède / utilise l'ancre non-personne
        if hub and anchor_id and not anchor_is_person and hub != anchor_id:
            self.add_edge(hub, anchor_id, sem.get(anchor_kind, "related_to"),
                          confidence=0.7, sources=[src_tag])

        new_ids = set(self._index()) - before
        return [n for n in self.data["nodes"] if n["id"] in new_ids]

    # ---- rendu -----------------------------------------------------
    def render(self, case_dir: str) -> dict:
        out = {"json": self.path}
        dot = _to_dot(self.data)
        dot_path = os.path.join(case_dir, "graph.dot")
        with open(dot_path, "w", encoding="utf-8") as fh:
            fh.write(dot)
        out["dot"] = dot_path
        svg = None
        try:
            import subprocess
            svg_path = os.path.join(case_dir, "graph.svg")
            subprocess.run(["dot", "-Tsvg", "-o", svg_path, dot_path], check=True,
                           timeout=60, capture_output=True)
            svg = svg_path
            out["svg"] = svg_path
        except Exception:
            pass
        html_path = os.path.join(case_dir, "graph.html")
        with open(html_path, "w", encoding="utf-8") as fh:
            fh.write(_graph_html(self.data, os.path.basename(svg) if svg else None))
        out["html"] = html_path
        return out


# ---------------------------------------------------------------------------
def _merge_attrs(dst: dict, extra: dict) -> None:
    for k, v in (extra or {}).items():
        if v in (None, "", [], {}):
            continue
        if isinstance(v, list):
            cur = dst.setdefault(k, [])
            for it in v:
                if it not in cur:
                    cur.append(it)
        elif k not in dst or not dst[k]:
            dst[k] = v


def _name_attrs(name: str) -> dict:
    f, l = split_name(name)
    return {"first_name": f, "last_name": l}


def _person_label(name: str) -> str:
    f, l = split_name(name)
    return (f"{l.upper()} {f}".strip() if l else name).strip()


def _to_dot(data: dict) -> str:
    color = {"person": "#ffd479", "email": "#7fd1ff", "phone": "#9be29b",
             "username": "#c9a0ff", "account": "#ff9ec7", "address": "#ffb38a",
             "organization": "#8ad4d4", "domain": "#bdbdbd", "ip": "#bdbdbd",
             "photo": "#dddddd", "url": "#bdbdbd"}
    lines = ['digraph osint {', '  bgcolor="#0f1115";', '  node [style=filled,fontname="Helvetica",fontsize=10,color="#333"];',
             '  edge [color="#8899aa",fontname="Helvetica",fontsize=8,fontcolor="#8899aa"];']
    for n in data["nodes"]:
        lbl = n["label"].replace('"', "'")
        lines.append(f'  "{n["id"]}" [label="{lbl}\\n({n["kind"]})",fillcolor="{color.get(n["kind"], "#ccc")}"];')
    for e in data["edges"]:
        lines.append(f'  "{e["src"]}" -> "{e["dst"]}" [label="{e["rel"]}"];')
    lines.append("}")
    return "\n".join(lines)


def _graph_html(data: dict, svg_name: str | None) -> str:
    body = (f'<object type="image/svg+xml" data="{svg_name}" style="width:100%;min-height:70vh"></object>'
            if svg_name else '<p>Graphviz (<code>dot</code>) absent — importez <code>graph.json</code> '
                             'dans Maltego / Gephi / yEd.</p>')
    rows = "\n".join(
        f"<tr><td>{n['kind']}</td><td>{_esc(n['label'])}</td><td>{n['confidence']}</td>"
        f"<td>{_esc(', '.join(n['sources'][:6]))}</td></tr>" for n in data["nodes"])
    return f"""<!doctype html><meta charset=utf-8><title>Graphe — {data.get('case','')}</title>
<style>body{{font:14px/1.5 system-ui,sans-serif;background:#0f1115;color:#d7dae0;margin:1.4rem}}
h1{{color:#7fd1ff}} table{{border-collapse:collapse;width:100%;margin-top:1rem}}
td,th{{border:1px solid #333;padding:4px 8px;text-align:left}} a{{color:#7fd1ff}}</style>
<h1>Graphe d'enquête — {data.get('case','')}</h1>
{body}
<h2>Nœuds ({len(data['nodes'])}) · Liens ({len(data['edges'])})</h2>
<table><tr><th>type</th><th>libellé</th><th>confiance</th><th>sources</th></tr>{rows}</table>"""


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------------------
def _main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    cmd = argv[0]
    if cmd == "merge":
        case_dir, jsonl = argv[1], argv[2]
        run = anchor = None
        rest = argv[3:]
        for i, a in enumerate(rest):
            if a == "--run" and i + 1 < len(rest):
                run = rest[i + 1]
            if a == "--anchor" and i + 1 < len(rest):
                anchor = rest[i + 1]
        sels = []
        with open(jsonl, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    sels.append(json.loads(line))
        g = Graph.load(case_dir)
        newn = g.merge_selectors(sels, run=run, anchor=anchor)
        g.save()
        for n in newn:
            print(f"{n['kind']}\t{n['label']}\t{n['confidence']}")
        return 0
    if cmd == "render":
        g = Graph.load(argv[1])
        out = g.render(argv[1])
        for k, v in out.items():
            print(f"{k}\t{v}")
        return 0
    if cmd == "show":
        g = Graph.load(argv[1])
        print(json.dumps(g.data, ensure_ascii=False, indent=2))
        return 0
    print("commande inconnue", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
