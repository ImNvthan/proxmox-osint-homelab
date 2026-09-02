#!/usr/bin/env bash
# /opt/osint/lib/common.sh — plomberie partagée par tous les pipelines osint-*.
# À charger par « source », jamais à exécuter directement.

OSINT_HOME="${OSINT_HOME:-/opt/osint}"
OSINT_RUNS="${OSINT_RUNS:-$OSINT_HOME/runs}"
OSINT_CASES="${OSINT_CASES:-$OSINT_HOME/cases}"
OSINT_WORDLISTS="${OSINT_WORDLISTS:-$OSINT_HOME/wordlists}"
OSINT_ENV="${OSINT_ENV:-/etc/osint/osint.env}"
OSINT_LIB="${OSINT_LIB:-$OSINT_HOME/lib}"
OSINT_STEP_TIMEOUT="${OSINT_STEP_TIMEOUT:-600}"   # secondes par outil, plafond strict
OSINT_HTTP_PORT="${OSINT_HTTP_PORT:-8899}"
OSINT_WEB_PORT="${OSINT_WEB_PORT:-8080}"
OSINT_REGION="${OSINT_REGION:-FR}"                # région par défaut pour les numéros
OSINT_PY="${OSINT_PY:-python3}"

# Autopilote
OSINT_AUTO_MAX_DEPTH="${OSINT_AUTO_MAX_DEPTH:-2}"
OSINT_AUTO_MAX_NODES="${OSINT_AUTO_MAX_NODES:-40}"
OSINT_AUTO_MIN_CONF="${OSINT_AUTO_MIN_CONF:-0.55}"
OSINT_AUTO_RECURSE_RELATIONS="${OSINT_AUTO_RECURSE_RELATIONS:-0}"
OSINT_ALLOW_RELATIONS="${OSINT_ALLOW_RELATIONS:-0}"
OSINT_ASSUME_YES="${OSINT_ASSUME_YES:-0}"

# Charge la config utilisateur / les clés d'API si présentes
if [[ -f "$OSINT_ENV" ]]; then
  set -a; # shellcheck source=/dev/null
  . "$OSINT_ENV"; set +a
fi

# osintkit est importable
export PYTHONPATH="${OSINT_LIB}:${PYTHONPATH:-}"

if [[ -t 1 ]]; then
  C_Y=$'\033[33m'; C_G=$'\033[1;92m'; C_R=$'\033[31m'; C_B=$'\033[36m'; C_D=$'\033[2m'; C_0=$'\033[m'
else
  C_Y=""; C_G=""; C_R=""; C_B=""; C_D=""; C_0=""
fi

log()  { echo -e "${C_B}[*]${C_0} $*"; }
ok()   { echo -e "${C_G}[+]${C_0} $*"; }
warn() { echo -e "${C_Y}[!]${C_0} $*" >&2; }
die()  { echo -e "${C_R}[x]${C_0} $*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

slugify() { echo "$1" | tr '[:upper:]' '[:lower:]' | sed 's#[^a-z0-9._-]#_#g' | cut -c1-80; }

# classify <valeur> -> "kind\tvaleur normalisée"
classify() { "$OSINT_PY" -m osintkit.classify "$1" "${2:-$OSINT_REGION}" 2>/dev/null; }

# case_dir : répertoire de l'enquête courante, ou vide
case_dir() { [[ -n "${OSINT_CASE:-}" ]] && echo "${OSINT_CASES}/${OSINT_CASE}"; }

case_status() {
  local cd; cd="$(case_dir)" || return 0
  [[ -n "$cd" ]] && { mkdir -p "$cd"; echo "$*" >"$cd/status"; }
}

# new_run <type> <cible>  -> affiche le chemin du nouveau répertoire d'exécution
new_run() {
  local type="$1" target="$2" ts dir base
  ts="$(date +%Y%m%d-%H%M%S)"
  if [[ -n "${OSINT_CASE:-}" ]]; then
    base="${OSINT_CASES}/${OSINT_CASE}/runs"
  else
    base="$OSINT_RUNS"
  fi
  dir="${base}/${type}_$(slugify "$target")_${ts}"
  mkdir -p "$dir/raw" "$dir/logs"
  RUNDIR="$dir"
  {
    printf 'type=%q\n'    "$type"
    printf 'target=%q\n'  "$target"
    printf 'started=%q\n' "$(date -Is)"
    printf 'host=%q\n'    "$(hostname)"
    [[ -n "${OSINT_CASE:-}" ]] && printf 'caseid=%q\n' "$OSINT_CASE"
  } >"$dir/meta.env"
  printf 'etape\trc\tsecondes\tsortie\n' >"$dir/manifest.tsv"
  echo "$dir"
}

# run <nom-etape> <fichier-sortie-relatif-a-raw> -- <commande...>
run() {
  local step="$1" outfile="$2" ; shift 2
  [[ "$1" == "--" ]] && shift
  local logf="$RUNDIR/logs/${step}.log" outp="$RUNDIR/raw/${outfile}"
  local t0 t1 rc
  log "${step} …"
  t0=$(date +%s)
  if [[ -n "$outfile" ]]; then
    timeout "$OSINT_STEP_TIMEOUT" "$@" >"$outp" 2>"$logf"; rc=$?
  else
    timeout "$OSINT_STEP_TIMEOUT" "$@" >"$logf" 2>&1; rc=$?
  fi
  t1=$(date +%s)
  printf '%s\t%s\t%s\t%s\n' "$step" "$rc" "$((t1-t0))" "${outfile:-–}" >>"$RUNDIR/manifest.tsv"
  if [[ $rc -eq 0 ]]; then ok "${step} terminé ($((t1-t0))s)"
  elif [[ $rc -eq 124 ]]; then warn "${step} a dépassé le délai de ${OSINT_STEP_TIMEOUT}s"
  else warn "${step} s'est terminé rc=${rc} (voir logs/${step}.log)"; fi
  return 0
}

run_sh() {
  local step="$1" outfile="$2"; shift 2
  run "$step" "$outfile" -- bash -c "$*"
}

require_target() { [[ -n "${1:-}" ]] || die "usage : $(basename "$0") <cible>"; }

# garde-fou : confirmation avant de traiter des données personnelles
confirm_personal() {
  local what="$1"
  [[ "${OSINT_ASSUME_YES}" == "1" || "${OSINT_ASSUME_YES}" == "yes" ]] && return 0
  [[ -t 0 && -t 1 ]] || return 0   # non interactif -> on suppose le périmètre validé en amont
  echo -e "${C_Y}Cible : ${what}${C_0}"
  echo    "Ceci traite des données personnelles. Confirmez une base légale (autorisation,"
  echo    "périmètre signé, intérêt légitime documenté…).  Voir docs/LEGAL.md."
  read -r -p "Continuer ? [o/N] " a
  [[ "$a" =~ ^[oOyY]$ ]] || die "annulé."
}

finish_run() {
  printf 'finished=%q\n' "$(date -Is)" >>"$RUNDIR/meta.env"
  # rapport HTML autonome de l'exécution
  if have osint-report; then osint-report "$RUNDIR" >/dev/null 2>&1 || warn "génération du rapport en échec"; fi
  # si dans une enquête : extraction des sélecteurs + fusion dans le graphe
  if [[ -n "${OSINT_CASE:-}" ]]; then
    local cdir="${OSINT_CASES}/${OSINT_CASE}"
    "$OSINT_PY" -m osintkit.extract "$RUNDIR" --region "$OSINT_REGION" >/dev/null 2>>"$cdir/engine.log" || \
      warn "extraction des sélecteurs en échec"
    if [[ -s "$RUNDIR/selectors.jsonl" ]]; then
      "$OSINT_PY" -m osintkit.graph merge "$cdir" "$RUNDIR/selectors.jsonl" \
        --run "$(basename "$RUNDIR")" ${OSINT_ANCHOR:+--anchor "$OSINT_ANCHOR"} \
        >>"$cdir/engine.log" 2>&1 || warn "fusion dans le graphe en échec"
    fi
  fi
  ok "exécution terminée → ${RUNDIR}"
  echo "$RUNDIR"
}

# curl avec des valeurs par défaut raisonnables
oget() { curl -fsSL --max-time 30 -A "Mozilla/5.0 (osint-lxc)" "$@"; }
