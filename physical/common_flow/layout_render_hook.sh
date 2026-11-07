#!/bin/bash
# KW-FIX-25/AUTORENDER 11-06 (OWNER "visually inspect the layout ... remove congestion" + bad-smell list): advisory layout
# PNGs + smells.json of every kit build, in <kit>/run/layout_review/{place,grt,route}/.
#   layout_render_hook.sh ORFS_STAGE RC     called by flow.sh's EXIT trap (grt183_make.sh patches the disposable container
#                                           copy), so it runs right after a stage process ended and before the next starts.
# ADVISORY ONLY: reads the stage ODB, writes only under run/layout_review; always returns 0; every step timeout-bounded
# (OT_LAYOUT_RENDER_TIMEOUT, default 300 s per render).  Opt out: OT_LAYOUT_RENDER=0 or 'export OT_LAYOUT_RENDER = 0' in config.mk.
main() {
  local stage=$1 src=$2 W=${OT_GRT183_WORK:-/work}
  [ "${OT_LAYOUT_RENDER:-1}" = 0 ] && return 0
  grep -q '^ *export OT_LAYOUT_RENDER *[:?]*= *0' "$W/config.mk" 2>/dev/null && return 0
  local labels
  case "$stage" in
    3_3_place_gp) [ "$src" != 0 ] || return 0; labels="place" ;;     # global place failed: its -failed ODB
    3_5_place_dp) labels="place" ;;
    5_1_grt) labels="place grt" ;;     # place: only when not rendered yet (stage resume hardlinks the earlier steps)
    5_2_route) labels="place grt route" ;;
    *) return 0 ;;
  esac
  local R=${RESULTS_DIR:-}
  [ -n "$R" ] && [ -d "$R" ] || R=$(ls -d "$W"/run/results/asap7/*/base 2>/dev/null | head -1)
  [ -n "$R" ] || return 0
  local here; here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
  [ -f "$here/layout_render.tcl" ] || return 0
  local L
  for L in $labels; do render_one "$L" "$W" "$R" "$here"; done
  return 0
}
newest() { ls -t "$@" 2>/dev/null | head -1; }
render_one() {
  local L=$1 W=$2 R=$3 here=$4 O odb
  case "$L" in
    place) odb=$(newest "$R/3_5_place_dp.odb" "$R/3_place.odb" "$R/3_5_place_dp-failed.odb" "$R/3_3_place_gp-failed.odb") ;;
    grt) odb=$(newest "$R/5_1_grt.odb" "$R/5_1_grt-failed.odb") ;;
    route) odb=$(newest "$R/5_2_route.odb") ;;
  esac
  [ -n "$odb" ] && [ -f "$odb" ] || return 0
  O=$W/run/layout_review/$L
  local stamp; stamp="$(basename "$odb") $(stat -c '%s %Y' "$odb" 2>/dev/null)"
  [ "$(cat "$O/.stamp" 2>/dev/null)" = "$stamp" ] && return 0
  mkdir -p "$O" || return 0
  local free; free=$(df -Pm "$O" 2>/dev/null | awk 'NR==2{print $4}')
  if [ -n "$free" ] && [ "$free" -lt 500 ]; then echo "OT_LAYOUT_RENDER $L: skipped, only ${free} MB free"; return 0; fi
  local T=${OT_LAYOUT_RENDER_TIMEOUT:-300} OR=${OPENROAD_EXE:-openroad} t0=$SECONDS rc=0
  rm -f "$O"/*.png "$O"/smells.json "$O"/smells.one "$O"/marks.tsv "$O"/.stamp
  (
    ulimit -c 0
    cd "$O" || exit 0
    export QT_QPA_PLATFORM=offscreen XDG_RUNTIME_DIR=/tmp/ot_lr_$$ OT_LR_ODB="$odb" OT_LR_OUT="$O" OT_LR_LABEL="$L" OT_LR_TOOLS="$here" \
           OT_LR_SMELL_TIMEOUT=$(( T > 150 ? T / 2 : 75 ))
    mkdir -p "$XDG_RUNTIME_DIR"
    timeout -k 20 "$T" "$OR" -no_splash -no_init -threads 1 -gui "$here/layout_render.tcl" </dev/null >"$O/render.log" 2>&1
    echo $? > "$O/.rc"
    rm -rf "$XDG_RUNTIME_DIR"
  )
  rc=$(cat "$O/.rc" 2>/dev/null || echo 1); rm -f "$O/.rc"
  echo "$stamp" > "$O/.stamp"      # also after a failed render: advisory, a stage is tried once
  local sum="" n; n=$(ls "$O"/*.png 2>/dev/null | wc -l)
  [ -f "$O/smells.one" ] && sum=$(head -c 400 "$O/smells.one")
  [ -n "$sum" ] || sum="no smells.json (see render.log)"
  [ "$rc" = 0 ] || sum="render rc $rc; $sum"
  local line="OT_LAYOUT_RENDER $L $(date -u '+%F %T') ${n} PNG $((SECONDS - t0)) s: $sum"
  echo "$line" | tee -a "$W/run/layout_review/summary.txt"
}
main "${1:-}" "${2:-0}" 2>/dev/null
exit 0
