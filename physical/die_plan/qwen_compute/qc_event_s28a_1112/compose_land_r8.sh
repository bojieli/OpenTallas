#!/bin/bash
# COMPOSE STEP: land_r8 is derived from a bind of (plan, manifest), never carried (QC-S28-A 11-12, class fix).
# usage: compose_land_r8.sh TREE PLAN OUTDIR [ELAB_CACHE_DIR]
#   TREE  = the event's source tree (repo root; manifest + land_r8 table inside it, repo-relative)
#   PLAN  = plan path (absolute or TREE-relative); OUTDIR = work dir for the two binds and the reports
#   ELAB_CACHE_DIR (optional) = a bind dir of the same manifest elaboration (asbuilt.json ...), hard-linked in
# Steps: (1) strict bind with the tree's current table (rc 0 or R8_STALE; bus_groups.json is written either way)
#        (2) land_r8_derive.py derive -> the tree's table (atomic replace; byte-identical to r8.py pads)
#        (3) if the table changed: strict bind again; (4) land_r8_derive.py check on the final bus_groups (exit 0)
set -uo pipefail
T=$1; PL=$2; O=$3; G=${4:-}
RT=physical/die_plan/qwen_compute/qc_start_1106/runtime
M=$T/$RT/asbuilt_sw2_pv.json
TAB=$T/$(python3 -I -c "import json,sys; print(json.load(open(sys.argv[1]))['land_r8'])" "$M")
mkdir -p "$O"
bind() {  # $1 = out dir name
  local B=$O/$1; rm -rf "$B"; mkdir -p "$B"
  if [ -n "$G" ]; then for f in asbuilt.json asbuilt.yosys.log asbuilt.ys asbuilt_lib_stubs.sv asbuilt_sources.json provenance_elab.json; do
    [ -e "$G/$f" ] && ln -f "$G/$f" "$B/$f"; done; fi
  (cd "$T" && nice -n 19 python3 -I -B -X faulthandler tools/die_plan/bind.py bind "$PL" --out "$B" --asbuilt "$M" --strict > "$B.log" 2>&1)
  echo $?
}
s0=$(sha256sum < "$TAB" | cut -c1-12)
rc1=$(bind bind1); echo "BIND1 rc=$rc1 table=$s0 R8_STALE=$(grep -c R8_STALE "$O/bind1.log")"
[ -s "$O/bind1/bus_groups.json" ] || { echo "BIND1 wrote no bus_groups.json"; exit 2; }
(cd "$T" && python3 -I tools/die_plan/land_r8_derive.py derive "$PL" "$O/bind1/bus_groups.json" --like "$TAB" --out "$TAB" --json "$O/derive.json") || exit 2
s1=$(sha256sum < "$TAB" | cut -c1-12)
FIN=bind1
if [ "$rc1" != 0 ] || [ "$s0" != "$s1" ]; then rc2=$(bind bind2); FIN=bind2; echo "BIND2 rc=$rc2 table=$s1"; [ "$rc2" = 0 ] || exit 1; fi
(cd "$T" && python3 -I tools/die_plan/land_r8_derive.py check "$PL" "$O/$FIN/bus_groups.json" --table "$TAB" --json "$O/check.json") || exit 1
echo "LAND_R8_COMPOSED table=$s1 bind=$O/$FIN"
