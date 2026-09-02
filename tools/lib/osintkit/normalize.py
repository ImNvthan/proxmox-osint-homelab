#!/usr/bin/env python3
"""Normalisation des sélecteurs : téléphones, e-mails, pseudos, URLs, noms."""
from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlparse

try:  # facultatif mais fortement recommandé
    import phonenumbers
    from phonenumbers import carrier, geocoder, number_type, PhoneNumberType
except Exception:  # pragma: no cover
    phonenumbers = None

# host -> nom de plateforme normalisé (réseaux sociaux + dev + forums courants)
PLATFORMS = {
    "twitter.com": "twitter", "x.com": "twitter", "nitter.net": "twitter",
    "instagram.com": "instagram", "facebook.com": "facebook", "fb.com": "facebook",
    "m.facebook.com": "facebook", "linkedin.com": "linkedin", "tiktok.com": "tiktok",
    "youtube.com": "youtube", "snapchat.com": "snapchat", "pinterest.com": "pinterest",
    "pinterest.fr": "pinterest", "reddit.com": "reddit", "github.com": "github",
    "gitlab.com": "gitlab", "keybase.io": "keybase", "t.me": "telegram",
    "telegram.me": "telegram", "mastodon.social": "mastodon", "medium.com": "medium",
    "twitch.tv": "twitch", "vk.com": "vk", "ok.ru": "odnoklassniki",
    "flickr.com": "flickr", "soundcloud.com": "soundcloud", "spotify.com": "spotify",
    "vimeo.com": "vimeo", "dribbble.com": "dribbble", "behance.net": "behance",
    "about.me": "about.me", "gravatar.com": "gravatar", "tumblr.com": "tumblr",
    "wordpress.com": "wordpress", "blogspot.com": "blogger", "onlyfans.com": "onlyfans",
    "patreon.com": "patreon", "buymeacoffee.com": "buymeacoffee", "ko-fi.com": "ko-fi",
    "strava.com": "strava", "goodreads.com": "goodreads", "last.fm": "lastfm",
    "copainsdavant.linternaute.com": "copainsdavant", "trombi.com": "trombi",
    "viadeo.com": "viadeo", "leboncoin.fr": "leboncoin", "discord.com": "discord",
    "bsky.app": "bluesky", "threads.net": "threads",
}


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s or "") if not unicodedata.combining(c))


def slug(s: str, maxlen: int = 80) -> str:
    s = strip_accents(s).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:maxlen] or "x"


def norm_email(e: str) -> str:
    return (e or "").strip().strip("<>").lower()


def norm_username(u: str) -> str:
    return (u or "").strip().lstrip("@").strip()


def platform_from_host(host: str) -> str | None:
    host = (host or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if host in PLATFORMS:
        return PLATFORMS[host]
    # sous-domaines : truc.medium.com, user.tumblr.com, user.wordpress.com
    for base, name in PLATFORMS.items():
        if host.endswith("." + base):
            return name
    return None


def platform_from_url(url: str) -> tuple[str | None, str | None]:
    """(plateforme, handle) à partir d'une URL de profil."""
    try:
        u = urlparse(url if "://" in url else "https://" + url)
    except Exception:
        return (None, None)
    host = (u.hostname or "").lower()
    plat = platform_from_host(host)
    parts = [p for p in u.path.split("/") if p]
    handle = None
    if parts:
        handle = parts[1] if parts[0] in {"in", "u", "user", "users", "@"} and len(parts) > 1 else parts[0]
        handle = handle.lstrip("@")
    return (plat, handle)


def norm_phone(raw: str, region: str = "FR") -> tuple[str | None, dict]:
    """Retourne (E.164|None, meta) — meta: region, carrier, type, valid."""
    meta: dict = {}
    if not raw:
        return (None, meta)
    if phonenumbers is None:
        d = re.sub(r"\D", "", raw)
        if raw.strip().startswith("+"):
            return ("+" + d, meta)
        return (None, meta)
    try:
        pn = phonenumbers.parse(raw, None if raw.strip().startswith("+") else region)
    except Exception:
        return (None, meta)
    meta["valid"] = phonenumbers.is_valid_number(pn)
    meta["region"] = geocoder.description_for_number(pn, "fr") or geocoder.region_code_for_number(pn)
    meta["carrier"] = carrier.name_for_number(pn, "fr")
    t = number_type(pn)
    meta["type"] = {
        PhoneNumberType.MOBILE: "mobile",
        PhoneNumberType.FIXED_LINE: "fixe",
        PhoneNumberType.FIXED_LINE_OR_MOBILE: "fixe/mobile",
        PhoneNumberType.VOIP: "voip",
        PhoneNumberType.TOLL_FREE: "numéro vert",
    }.get(t, "autre")
    e164 = phonenumbers.format_number(pn, phonenumbers.PhoneNumberFormat.E164)
    if not meta["valid"]:
        return (e164, meta)
    return (e164, meta)


_PARTICLES = {"de", "du", "des", "la", "le", "van", "von", "di", "da", "el", "al", "bin", "ben"}


def split_name(full: str) -> tuple[str, str]:
    """('Jean', 'Dupont') — gère « Jean-Pierre de La Fontaine »."""
    toks = [t for t in re.split(r"\s+", (full or "").strip()) if t]
    if not toks:
        return ("", "")
    if len(toks) == 1:
        return (toks[0], "")
    first = toks[0]
    rest = toks[1:]
    # regroupe les particules avec le nom qui suit
    last_parts: list[str] = []
    i = 0
    while i < len(rest):
        w = rest[i]
        if w.lower() in _PARTICLES and i + 1 < len(rest):
            last_parts.append(w)
        else:
            last_parts.append(w)
        i += 1
    return (first, " ".join(last_parts))


def username_permutations(first: str, last: str) -> list[str]:
    f = slug(first).replace("-", "")
    l = slug(last).replace("-", "")
    if not f and not l:
        return []
    fi, li = (f[:1], l[:1])
    cands = [
        f + l, f + "." + l, f + "_" + l, f + "-" + l, fi + l, f + li,
        l + f, l + "." + f, fi + "." + l, f, l, l + "." + f, f + l + "1",
    ]
    seen, out = set(), []
    for c in cands:
        c = c.strip("._-")
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def email_permutations(first: str, last: str, domains: list[str]) -> list[str]:
    f = slug(first).replace("-", "")
    l = slug(last).replace("-", "")
    users = [u for u in {f + "." + l, f + l, f[:1] + l, f + "_" + l, f, l + f} if u.strip("._")]
    return [f"{u}@{d}" for d in domains for u in users]
