#!/usr/bin/env python3
"""Détection du type d'un sélecteur saisi par l'utilisateur.

    python3 -m osintkit.classify "+33 6 12 34 56 78"      -> phone   +33612345678
    python3 -m osintkit.classify "jean.dupont@gmail.com"  -> email   jean.dupont@gmail.com
    python3 -m osintkit.classify "jdupont"                -> username jdupont
    python3 -m osintkit.classify "Jean Dupont"            -> person  Jean Dupont
    python3 -m osintkit.classify "https://x.com/jdupont"  -> account x.com/jdupont
    python3 -m osintkit.classify "example.com"            -> domain  example.com
    python3 -m osintkit.classify "8.8.8.8"               -> ip      8.8.8.8

Sortie : une ligne « <kind>\t<valeur normalisée> ». `kind` ∈
{phone,email,username,person,account,domain,ip,url,unknown}.
"""
from __future__ import annotations

import ipaddress
import re
import sys
from urllib.parse import urlparse

from .normalize import norm_phone, platform_from_host

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
_DOMAIN_RE = re.compile(r"^(?=.{4,253}$)([a-z0-9](-?[a-z0-9])*\.)+[a-z]{2,24}$", re.I)
_HANDLE_RE = re.compile(r"^@?[a-z0-9](?:[a-z0-9._-]{1,38}[a-z0-9])?$", re.I)
_PHONEISH_RE = re.compile(r"^\+?[\d][\d\s().\-/]{5,}$")


def classify(raw: str, default_region: str = "FR") -> tuple[str, str]:
    s = (raw or "").strip()
    if not s:
        return ("unknown", "")

    # URL explicite -> account (si plateforme connue) sinon url/domain
    if re.match(r"^[a-z][a-z0-9+.-]*://", s, re.I):
        u = urlparse(s)
        host = (u.hostname or "").lower().lstrip("www.")
        plat = platform_from_host(host)
        path = u.path.strip("/")
        if plat and path:
            return ("account", f"{host}/{path.split('/')[0]}")
        if host and not path:
            return ("domain", host)
        return ("url", s)

    if _EMAIL_RE.match(s):
        return ("email", s.lower())

    # IP / CIDR
    try:
        ipaddress.ip_network(s, strict=False)
        return ("ip", s)
    except ValueError:
        pass

    # Téléphone : contient surtout des chiffres, éventuellement un +
    digits = re.sub(r"\D", "", s)
    if _PHONEISH_RE.match(s) and 7 <= len(digits) <= 15:
        e164 = norm_phone(s, default_region)[0]
        return ("phone", e164 or ("+" + digits if s.startswith("+") else digits))

    if _DOMAIN_RE.match(s) and " " not in s:
        return ("domain", s.lower())

    # Nom complet : au moins deux mots alphabétiques
    words = [w for w in re.split(r"[\s]+", s) if w]
    alpha_words = [w for w in words if re.search(r"[^\W\d_]", w, re.UNICODE)]
    if len(words) >= 2 and len(alpha_words) >= 2:
        return ("person", " ".join(words))

    # Un seul jeton -> pseudo
    if len(words) == 1 and _HANDLE_RE.match(s):
        return ("username", s.lstrip("@"))

    if len(words) == 1 and re.search(r"[^\W\d_]", s, re.UNICODE):
        return ("username", s)

    return ("unknown", s)


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: python3 -m osintkit.classify <valeur> [region]", file=sys.stderr)
        return 2
    region = argv[1] if len(argv) > 1 else "FR"
    kind, value = classify(argv[0], region)
    print(f"{kind}\t{value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
