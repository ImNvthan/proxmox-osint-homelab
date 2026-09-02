#!/usr/bin/env bash
# ---------------------------------------------------------------------------
#  Homelab OSINT — script utilitaire Proxmox VE (v2)
#  Crée un conteneur Debian non privilégié avec un homelab OSINT complet :
#  autopilote (un sélecteur -> graphe d'entités + affiche), boîte à outils,
#  interface web.
#
#  À LANCER SUR L'HÔTE PROXMOX :
#    bash -c "$(wget -qLO - https://raw.githubusercontent.com/ImNvthan/proxmox-osint-homelab/main/ct/osint.sh)"
#
#  Auteur : Nathan Drancourt   ·   Licence : MIT
# ---------------------------------------------------------------------------
set -Eeo pipefail

REPO_BRANCH="${OSINT_REPO_BRANCH:-main}"
FUNC_BASE="${OSINT_FUNC_BASE:-https://raw.githubusercontent.com/ImNvthan/proxmox-osint-homelab/${REPO_BRANCH}/misc}"

_src="${BASH_SOURCE[0]:-}"
_local=""
if [[ -n "$_src" ]]; then
  _here="$(cd "$(dirname "$_src")" && pwd)"
  [[ -f "${_here}/../misc/build.func" ]] && _local="${_here}/../misc/build.func"
fi
if [[ -n "$_local" ]]; then
  # shellcheck source=/dev/null
  source "$_local"
else
  source <(curl -fsSL "${FUNC_BASE}/build.func") || {
    echo "Échec de la récupération de build.func depuis ${FUNC_BASE}" >&2; exit 1
  }
fi

APP="OSINT"
var_tags="osint;recon;security;autopilot"
var_os="debian"
var_version="12"
var_cpu="4"
var_ram="8192"
var_disk="40"
var_unprivileged="1"
var_hostname="osint"
var_bridge="vmbr0"
var_net="dhcp"
var_onboot="1"

root_check
pve_check
pkg_check
arch_check

start
build_container
description

echo
msg_ok "Terminé. Entrez avec « pct enter <ctid> » puis lancez « osint »."
