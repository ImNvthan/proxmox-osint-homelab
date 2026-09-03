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

REPO_SLUG="${OSINT_REPO_SLUG:-ImNvthan/proxmox-osint-homelab}"
REPO_BRANCH="${OSINT_REPO_BRANCH:-main}"
export OSINT_REPO_URL="${OSINT_REPO_URL:-https://github.com/${REPO_SLUG}}"
export OSINT_REPO_BRANCH="$REPO_BRANCH"

# build.func : copie locale si on tourne depuis un clone, sinon archive codeload
# (branche exacte, pas de cache raw.githubusercontent persistant).
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
  _bt="$(mktemp -d)"
  if curl -fsSL --retry 6 --retry-all-errors --retry-delay 4 --connect-timeout 20 \
       "https://codeload.github.com/${REPO_SLUG}/tar.gz/refs/heads/${REPO_BRANCH}" -o "$_bt/r.tgz" \
     && tar -xzf "$_bt/r.tgz" -C "$_bt" --strip-components=1 2>/dev/null \
     && [[ -f "$_bt/misc/build.func" ]]; then
    # shellcheck source=/dev/null
    source "$_bt/misc/build.func"
  else
    echo "Échec de la récupération de https://github.com/${REPO_SLUG} (branche ${REPO_BRANCH})" >&2
    exit 1
  fi
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
