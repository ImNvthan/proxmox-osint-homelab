#!/usr/bin/env bash
# ---------------------------------------------------------------------------
#  osint-install.sh — s'exécute DANS un LXC Debian 12 neuf en tant que root.
#  Provisionne la chaîne d'outils OSINT + le moteur d'autopilote `osintkit`
#  + la CLI `osint` + l'interface web.
#
#  Aussi utilisable à la main sur une machine Debian 12 / Ubuntu 22.04+ à vous.
#  Recommandé (immunisé contre le cache de raw.githubusercontent) :
#    curl -fsSL https://codeload.github.com/ImNvthan/proxmox-osint-homelab/tar.gz/refs/heads/main \
#      | tar xz && bash proxmox-osint-homelab-main/install/osint-install.sh
#
#  Licence : MIT
# ---------------------------------------------------------------------------
set -Eeuo pipefail

OSINT_REPO_URL="${OSINT_REPO_URL:-https://github.com/ImNvthan/proxmox-osint-homelab}"
OSINT_REPO_BRANCH="${OSINT_REPO_BRANCH:-main}"
GO_VERSION="${GO_VERSION:-1.22.6}"
SPIDERFOOT_BIND="${SPIDERFOOT_BIND:-127.0.0.1:5001}"
OSINT_WEB_BIND="${OSINT_WEB_BIND:-127.0.0.1}"
PREFIX=/opt/osint

# Jamais d'invite d'identifiants git bloquante : archives tar.gz via curl.
export GIT_TERMINAL_PROMPT=0

mkdir -p "$PREFIX" /etc/osint
: >/opt/osint/install.log

# --- bootstrap : une seule source de vérité = une archive du dépôt ----------
# Si on tourne depuis un clone / une archive extraite, on l'utilise. Sinon on
# télécharge l'archive codeload (branche exacte, pas de cache raw persistant).
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT=""
if [[ -d "$SELF_DIR/../tools" && -f "$SELF_DIR/../misc/install.func" ]]; then
  REPO_ROOT="$(cd "$SELF_DIR/.." && pwd)"
fi
if [[ -z "$REPO_ROOT" ]]; then
  _slug="${OSINT_REPO_URL#https://github.com/}"; _slug="${_slug%.git}"
  _bt="$(mktemp -d)"
  echo "➜ Récupération du dépôt ${_slug}@${OSINT_REPO_BRANCH} (archive)…"
  if curl -fsSL --retry 6 --retry-all-errors --retry-delay 4 --connect-timeout 20 \
       "https://codeload.github.com/${_slug}/tar.gz/refs/heads/${OSINT_REPO_BRANCH}" -o "$_bt/r.tgz" \
     && tar -xzf "$_bt/r.tgz" -C "$_bt"; then
    for _d in "$_bt"/*/; do [[ -d "$_d" ]] && REPO_ROOT="${_d%/}" && break; done
  fi
  if [[ ! -d "${REPO_ROOT:-/nonexistent}/tools" ]]; then
    echo "FATAL : impossible de récupérer ${OSINT_REPO_URL} (réseau / GitHub indisponible)." >&2
    echo "        Réessayez dans quelques minutes, ou :" >&2
    echo "        curl -fsSL https://codeload.github.com/${_slug}/tar.gz/refs/heads/${OSINT_REPO_BRANCH} | tar xz && bash */install/osint-install.sh" >&2
    exit 1
  fi
fi

# shellcheck source=/dev/null
source "$REPO_ROOT/misc/install.func"
command -v msg_ok >/dev/null && command -v fetch_src >/dev/null \
  || { echo "FATAL : install.func incomplet (${REPO_ROOT}/misc/install.func)"; exit 1; }

trap 'msg_error "Erreur ligne $LINENO. Installation partielle conservée ; voir /opt/osint/install.log"; exit 1' ERR

# =======================================================================
section "Système de base"
export DEBIAN_FRONTEND=noninteractive
try "apt update"   apt-get -qq update
try "apt upgrade"  apt-get -qq -y upgrade
try "locales/tz"   apt_install locales tzdata ca-certificates

APT_BASE=(
  curl wget git jq jo unzip zip xz-utils gnupg lsb-release apt-transport-https
  build-essential python3 python3-pip python3-venv python3-dev pipx
  libffi-dev libssl-dev libfuzzy-dev
  whois dnsutils bind9-dnsutils
  nmap tor torsocks proxychains4
  chromium libnss3 fonts-liberation
  libimage-exiftool-perl mediainfo tesseract-ocr poppler-utils
  ripgrep pandoc sqlite3 graphviz
  whatweb dnsrecon
  # moteur python (osintkit) — via apt pour éviter les venv fragiles
  python3-flask python3-jinja2 python3-requests python3-bs4 python3-lxml
  python3-phonenumbers python3-networkx python3-dateutil
)
section "Paquets APT"
try "apt : chaîne principale" apt_install "${APT_BASE[@]}"
for p in sublist3r yt-dlp masscan weasyprint; do try "apt : ${p}" apt_install "$p"; done

# =======================================================================
section "Go ${GO_VERSION} (outillage ProjectDiscovery)"
if ! /usr/local/go/bin/go version 2>/dev/null | grep -q "go${GO_VERSION}"; then
  arch="$(dpkg --print-architecture)"; [[ "$arch" == "amd64" ]] && garch="amd64" || garch="$arch"
  try_sh "téléchargement + extraction de Go" \
    "curl -fsSL https://go.dev/dl/go${GO_VERSION}.linux-${garch}.tar.gz -o /tmp/go.tgz && rm -rf /usr/local/go && tar -C /usr/local -xzf /tmp/go.tgz && rm /tmp/go.tgz"
fi
export PATH="/usr/local/go/bin:/usr/local/bin:$PATH"
mkdir -p /root/go

section "Outils Go"
go_install "github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest" subfinder
go_install "github.com/projectdiscovery/httpx/cmd/httpx@latest"            httpx
go_install "github.com/projectdiscovery/dnsx/cmd/dnsx@latest"             dnsx
go_install "github.com/projectdiscovery/katana/cmd/katana@latest"        katana
go_install "github.com/lc/gau/v2/cmd/gau@latest"                         gau
go_install "github.com/sensepost/gowitness@latest"                       gowitness
go_install "github.com/gitleaks/gitleaks/v8@latest"                      gitleaks
go_install "github.com/tomnomnom/assetfinder@latest"                     assetfinder
go_install "github.com/owasp-amass/amass/v4/...@master"                  amass

# =======================================================================
section "Outils OSINT Python (pipx, isolés)"
export PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin
retry 3 env PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install --pip-args=--no-cache-dir theHarvester \
  && msg_ok "pipx : theHarvester" || msg_warn "pipx : theHarvester — échec après 3 essais. On continue."
pipx_install "holehe"           holehe
pipx_install "maigret"          maigret
pipx_install "socialscan"       socialscan
pipx_install "sherlock-project" sherlock
pipx_install "dnstwist[full]"   dnstwist
pipx_install "checkdmarc"       checkdmarc
pipx_install "h8mail"           h8mail
pipx_install "waymore"          waymore
retry 2 env PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install --pip-args=--no-cache-dir recon-ng \
  && msg_ok "pipx : recon-ng" || msg_warn "pipx : recon-ng — échec (dépendances lourdes). On continue."
pipx_install "ignorant"         ignorant
pipx_install "toutatis"         toutatis
pipx_install "xeuledoc"         xeuledoc
pipx_install "ghunt"            ghunt
# blackbird : archive tar.gz (pas de git), puis pipx sur le dossier
if fetch_src "p1ngul1n0/blackbird" "main" /opt/blackbird; then
  try "pipx : blackbird" env PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin \
      pipx install --pip-args=--no-cache-dir /opt/blackbird
else
  msg_warn "blackbird — téléchargement impossible. On continue (sherlock+maigret couvrent les pseudos)."
fi

# =======================================================================
section "SpiderFoot (service systemd)"
if [[ ! -d /opt/spiderfoot ]]; then
  fetch_src "smicallef/spiderfoot" "master" /opt/spiderfoot \
    && msg_ok "SpiderFoot récupéré" \
    || msg_warn "SpiderFoot — téléchargement impossible. Service non installé (l'autopilote fonctionne sans)."
fi
if [[ -d /opt/spiderfoot && -f /opt/spiderfoot/requirements.txt ]]; then
  try_sh "venv SpiderFoot" \
    "python3 -m venv /opt/spiderfoot/.venv && /opt/spiderfoot/.venv/bin/pip -q install --no-cache-dir -r /opt/spiderfoot/requirements.txt"
  id spiderfoot &>/dev/null || useradd -r -d /opt/spiderfoot -s /usr/sbin/nologin spiderfoot
  chown -R spiderfoot:spiderfoot /opt/spiderfoot
  cat >/etc/systemd/system/spiderfoot.service <<EOF
[Unit]
Description=Automatisation OSINT SpiderFoot
After=network-online.target
Wants=network-online.target
[Service]
User=spiderfoot
WorkingDirectory=/opt/spiderfoot
ExecStart=/opt/spiderfoot/.venv/bin/python /opt/spiderfoot/sf.py -l ${SPIDERFOOT_BIND}
Restart=on-failure
[Install]
WantedBy=multi-user.target
EOF
  try "service SpiderFoot" systemctl enable --now spiderfoot.service
fi

section "PhoneInfoga"
try_sh "installation de phoneinfoga" \
  "curl -fsSL https://raw.githubusercontent.com/sundowndev/phoneinfoga/master/support/scripts/install -o /tmp/pi.sh && (cd /tmp && bash /tmp/pi.sh) && install -m0755 /tmp/phoneinfoga /usr/local/bin/phoneinfoga"

# =======================================================================
section "CLI OSINT + moteur osintkit + charge utile"
SRC=/opt/osint/src
# La charge utile vient de l'archive déjà récupérée au bootstrap ($REPO_ROOT).
rm -rf "$SRC"; mkdir -p "$SRC"; cp -a "$REPO_ROOT/." "$SRC/"
if [[ ! -d "$SRC/tools" ]]; then
  msg_error "charge utile tools/ absente sous $REPO_ROOT — installation impossible."
  exit 1
fi
msg_ok "charge utile en place ($SRC)"

if [[ -d "$SRC/tools" ]]; then
  install -d /usr/local/bin /opt/osint/lib /opt/osint/runs /opt/osint/cases /opt/osint/wordlists /etc/osint/monitors
  install -m0755 "$SRC"/tools/bin/*         /usr/local/bin/
  install -m0644 "$SRC"/tools/lib/common.sh /opt/osint/lib/common.sh
  rm -rf /opt/osint/lib/osintkit
  cp -r "$SRC/tools/lib/osintkit" /opt/osint/lib/osintkit
  [[ -f /etc/osint/osint.env ]] || install -m0600 "$SRC/tools/etc/osint.env.example" /etc/osint/osint.env
  install -m0644 "$SRC/tools/etc/motd" /etc/motd
  install -m0644 "$SRC"/tools/systemd/*.service "$SRC"/tools/systemd/*.timer /etc/systemd/system/
  # interface web : bind configurable
  sed -i -E "s#(--host )127\.0\.0\.1#\1${OSINT_WEB_BIND}#" /etc/systemd/system/osint-web.service || true
  systemctl daemon-reload
  try "timer de mise à jour" systemctl enable --now osint-update.timer
  try "interface web"        systemctl enable --now osint-web.service
  # sanity check du moteur
  PYTHONPATH=/opt/osint/lib python3 -m osintkit.classify "test@example.com" >>/opt/osint/install.log 2>&1 \
    && msg_ok "moteur osintkit opérationnel" || msg_warn "osintkit : vérification échouée (voir install.log)"
  msg_ok "CLI osint + moteur installés"
else
  msg_error "tools/ introuvable dans le clone — CLI non installée."
fi

# =======================================================================
section "Listes de mots"
try_sh "SecLists DNS top 5k" \
  "curl -fsSL --retry 5 --retry-all-errors --retry-delay 4 https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1million-5000.txt -o /opt/osint/wordlists/subdomains-5000.txt"

section "Confidentialité"
try "activation de Tor" systemctl enable --now tor.service

section "Nettoyage"
apt-get -qq -y autoremove >/dev/null 2>&1 || true
apt-get -qq clean || true

trap - ERR
echo
msg_ok "Homelab OSINT prêt."
IP="$(hostname -I | awk '{print $1}')"
cat <<EOF

 ${BOLD}Pour commencer :${CL}
   pct enter <ctid>                    # depuis l'hôte Proxmox
   osint                               # invite : « Que savez-vous ? »
   osint auto "+33612345678"           # autopilote en une ligne
   osint auto "Jean Dupont" --relations
   →  interface web : http://${IP}:8080   (osint web expose pour l'ouvrir au LAN)

   osint doctor                        # état des outils + du moteur
   nano /etc/osint/osint.env           # clés d'API facultatives
EOF
[[ -s /opt/osint/install-warnings.log ]] && \
  echo -e "\n ${YW}Avertissements de composants facultatifs — voir /opt/osint/install-warnings.log${CL}"
