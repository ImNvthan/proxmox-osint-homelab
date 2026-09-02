#!/usr/bin/env python3
"""Mini interface web du LXC OSINT — « saisir ce qu'on sait, ça cherche seul ».

    python3 -m osintkit.web --host 127.0.0.1 --port 8080 [--runs /opt/osint/cases]

Une page : un champ, un bouton. Lance `osint auto` en arrière-plan, montre la
progression, puis affiche le dossier + le graphe. Écoute sur 127.0.0.1 par
défaut ; `osint web expose` relance sur 0.0.0.0 (LAN de confiance uniquement).
"""
from __future__ import annotations

import html
import json
import os
import re
import subprocess
import sys
import time

CASES_DIR = os.environ.get("OSINT_CASES", "/opt/osint/cases")
OSINT_BIN = os.environ.get("OSINT_BIN", "osint")
BASIC_USER = os.environ.get("OSINT_WEB_USER", "")
BASIC_PASS = os.environ.get("OSINT_WEB_PASS", "")

try:
    from flask import Flask, Response, redirect, request, send_from_directory, url_for
except Exception:
    print("Flask absent : apt-get install -y python3-flask", file=sys.stderr)
    raise

app = Flask(__name__)
_procs: dict[str, subprocess.Popen] = {}


# --------------------------------------------------------------------------- #
def _auth_ok() -> bool:
    if not BASIC_USER:
        return True
    a = request.authorization
    return bool(a and a.username == BASIC_USER and a.password == BASIC_PASS)


@app.before_request
def _guard():
    if not _auth_ok():
        return Response("auth requise", 401, {"WWW-Authenticate": 'Basic realm="osint"'})


def _cases() -> list[dict]:
    out = []
    if not os.path.isdir(CASES_DIR):
        return out
    for name in sorted(os.listdir(CASES_DIR), reverse=True):
        d = os.path.join(CASES_DIR, name)
        gj = os.path.join(d, "graph.json")
        if not os.path.isdir(d):
            continue
        meta = {"id": name, "seed": "", "nodes": 0, "done": os.path.exists(os.path.join(d, "dossier.html"))}
        if os.path.exists(gj):
            try:
                g = json.load(open(gj, encoding="utf-8"))
                meta["nodes"] = len(g.get("nodes", []))
                s = g.get("seed") or {}
                meta["seed"] = f'{s.get("kind","?")}: {s.get("value","")}'
            except Exception:
                pass
        st = os.path.join(d, "status")
        meta["status"] = open(st, encoding="utf-8").read().strip() if os.path.exists(st) else ("terminé" if meta["done"] else "?")
        out.append(meta)
    return out


PAGE = """<!doctype html><html lang=fr><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>LXC OSINT</title>
<style>
body{{font:15px/1.6 system-ui,sans-serif;background:#0f1115;color:#e7eaf0;margin:0}}
.wrap{{max-width:760px;margin:6vh auto;padding:0 20px}}
h1{{color:#7fd1ff;font-size:24px}} .muted{{color:#93a1b3}}
form{{display:flex;gap:10px;margin:18px 0}}
input[type=text]{{flex:1;padding:12px 14px;border-radius:10px;border:1px solid #2a2f3a;background:#171a21;color:#e7eaf0;font-size:16px}}
button{{padding:12px 18px;border-radius:10px;border:0;background:#7fd1ff;color:#08141c;font-weight:700;cursor:pointer}}
label.opt{{display:block;margin:8px 0;color:#93a1b3}}
.card{{background:#171a21;border:1px solid #2a2f3a;border-radius:12px;padding:14px 16px;margin:10px 0}}
a{{color:#7fd1ff}} code{{color:#ffd479}}
.warn{{background:#3a2a12;border:1px solid #6b4c1d;color:#ffd9a8;border-radius:10px;padding:10px 14px;font-size:13px}}
table{{width:100%;border-collapse:collapse}} td,th{{border:1px solid #2a2f3a;padding:6px 9px;text-align:left}}
</style></head><body><div class=wrap>
<h1>LXC OSINT — autopilote</h1>
<p class=muted>Entrez <b>ce que vous savez</b> : numéro, e-mail, pseudo, nom complet, domaine ou IP.
Le type est détecté et les outils s'enchaînent seuls.</p>
<form method=post action="/run" id="mainform">
  <input type=text name=q placeholder="+33 6 12 34 56 78   ·   jean.dupont@gmail.com   ·   Jean Dupont" autofocus required>
  <button type=submit>Lancer</button>
</form>
<p class=muted><label><input type=checkbox name=relations value=1 form="mainform"> aussi chercher la <b>famille / les proches</b> (tiers — base légale RGPD requise)</label></p>
<div class=warn>Investigations autorisées uniquement. Données personnelles soumises au RGPD :
minimisez, justifiez, purgez (<code>osint case purge &lt;id&gt;</code>).</div>
<h2 class=muted style="font-size:15px;margin-top:28px">Enquêtes récentes</h2>
{cases}
</div></body></html>"""


@app.get("/")
def index():
    rows = ""
    for c in _cases():
        link = f'<a href="/case/{c["id"]}">{c["id"]}</a>'
        rows += (f'<div class="card">{link}<br><span class="muted">{html.escape(c["seed"])} · '
                 f'{c["nodes"]} entités · {html.escape(str(c["status"]))}</span></div>')
    return PAGE.format(cases=rows or '<p class="muted">aucune pour le moment</p>')


@app.post("/run")
def run():
    q = (request.form.get("q") or "").strip()
    if not q:
        return redirect(url_for("index"))
    relations = request.form.get("relations") == "1"
    cid = "web_" + time.strftime("%Y%m%d-%H%M%S")
    cmd = [OSINT_BIN, "auto", q, "--case", cid, "--yes"]
    if relations:
        cmd.append("--relations")
    env = dict(os.environ, OSINT_ASSUME_YES="1")
    os.makedirs(os.path.join(CASES_DIR, cid), exist_ok=True)
    logf = open(os.path.join(CASES_DIR, cid, "web.log"), "w")
    _procs[cid] = subprocess.Popen(cmd, stdout=logf, stderr=subprocess.STDOUT, env=env)
    return redirect(url_for("case", cid=cid))


@app.get("/case/<cid>")
def case(cid: str):
    cid = re.sub(r"[^A-Za-z0-9_.\-]", "", cid)
    d = os.path.join(CASES_DIR, cid)
    if not os.path.isdir(d):
        return "inconnu", 404
    done = os.path.exists(os.path.join(d, "dossier.html"))
    proc = _procs.get(cid)
    running = proc is not None and proc.poll() is None
    status = ""
    sp = os.path.join(d, "status")
    if os.path.exists(sp):
        status = open(sp, encoding="utf-8").read().strip()
    log = ""
    lp = os.path.join(d, "web.log")
    if os.path.exists(lp):
        log = html.escape(open(lp, encoding="utf-8", errors="replace").read()[-6000:])
    if done and not running:
        body = (f'<p><a href="/case/{cid}/dossier">Ouvrir le dossier</a> · '
                f'<a href="/case/{cid}/graph">graphe</a> · <a href="/">nouvelle recherche</a></p>'
                f'<iframe src="/case/{cid}/dossier" style="width:100%;height:78vh;border:1px solid #2a2f3a;border-radius:10px"></iframe>')
        refresh = ""
    else:
        body = (f'<p class="muted">Recherche en cours… <code>{html.escape(status)}</code></p>'
                f'<pre style="background:#12151b;padding:12px;border-radius:10px;max-height:60vh;overflow:auto">{log}</pre>')
        refresh = '<meta http-equiv="refresh" content="4">'
    return (f'<!doctype html><meta charset=utf-8>{refresh}<title>{cid}</title>'
            f'<style>body{{font:14px system-ui;background:#0f1115;color:#e7eaf0;margin:0}}'
            f'.wrap{{max-width:960px;margin:4vh auto;padding:0 18px}}a{{color:#7fd1ff}}code{{color:#ffd479}}</style>'
            f'<div class=wrap><h1 style="color:#7fd1ff">Enquête {cid}</h1>{body}</div>')


@app.get("/case/<cid>/dossier")
def dossier(cid):
    cid = re.sub(r"[^A-Za-z0-9_.\-]", "", cid)
    return send_from_directory(os.path.join(CASES_DIR, cid), "dossier.html")


@app.get("/case/<cid>/graph")
def graph(cid):
    cid = re.sub(r"[^A-Za-z0-9_.\-]", "", cid)
    return send_from_directory(os.path.join(CASES_DIR, cid), "graph.html")


@app.get("/case/<cid>/f/<path:sub>")
def casefile(cid, sub):
    cid = re.sub(r"[^A-Za-z0-9_.\-]", "", cid)
    return send_from_directory(os.path.join(CASES_DIR, cid), sub)


def main(argv: list[str]) -> int:
    host, port = "127.0.0.1", 8080
    if "--host" in argv:
        host = argv[argv.index("--host") + 1]
    if "--port" in argv:
        port = int(argv[argv.index("--port") + 1])
    if "--runs" in argv:
        globals()["CASES_DIR"] = argv[argv.index("--runs") + 1]
    print(f"[osint-web] http://{host}:{port}  (cases: {CASES_DIR})", file=sys.stderr)
    app.run(host=host, port=port, threaded=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
