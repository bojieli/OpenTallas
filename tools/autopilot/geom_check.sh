#!/bin/bash
# AUTO-GEOM rule check (read-only on the kit): dump a placed / CTS ODB with geom_dump.tcl in the pinned ORFS image
# (ODB dir mounted read-only), run the short GRT probe deck geom_grt.tcl on the same ODB in parallel (GEOM-AUTO-2
# 2026-10-27: >= 50 congestion iterations, kit MAX_ROUTING_LAYER), judge both with geom_rules.py and render the
# AUTO-GEOM image with geom_png.py.
#   geom_check.sh OUTDIR        OUTDIR/check.json = {"odb", "image", "id", "mem_gb", "rules_args": [...],
#                               optional "grt": false, "grt_max": "M5", "grt_iter": 50} from autopilot.py
# Writes OUTDIR/geom.tsv (dump), OUTDIR/grt.log + cong.rpt (GRT probe), OUTDIR/auto_geom.json (rule results),
# OUTDIR/auto_geom.png, prints "AP_AUTO_GEOM <verdict line>".
set -uo pipefail
OUT=$(cd "$1" && pwd)
TOOLS=$(cd "$(dirname "$0")" && pwd)
J() { python3 -I -c 'import json,sys;d=json.load(open(sys.argv[1]));v=d.get(sys.argv[2],sys.argv[3]);print(str(v).lower() if isinstance(v,bool) else v)' "$OUT/check.json" "$1" "$2"; }
ODB=$(J odb ""); IMG=$(J image openroad/orfs:asap7lock); ID=$(J id x); MEM=$(J mem_gb 8)
GRT=$(J grt true); GITER=$(J grt_iter 50)
test -f "$ODB" || { echo "AP_AUTO_GEOM_ERROR checkpoint missing: $ODB"; exit 2; }
OD=$(dirname "$ODB"); OB=$(basename "$ODB")
KIT=$(cd "$OD/../../../../.." 2>/dev/null && pwd)
kv() { [ -f "$KIT/config.mk" ] && sed -nE "s/^\s*(export\s+)?$1\s*[:?]?=\s*(\S+).*/\2/p" "$KIT/config.mk" | tail -1; }
GMAX=$(J grt_max "$(kv MAX_ROUTING_LAYER)"); GMAX=${GMAX:-M5}
GMIN=$(kv MIN_ROUTING_LAYER); GMIN=${GMIN:-M2}
GADJ=$(kv ROUTING_LAYER_ADJUSTMENT); GADJ=${GADJ:-0.25}   # ORFS asap7 platform default (config.mk ROUTING_LAYER_ADJUSTMENT ?= 0.25), as the flow GRT
DK=docker; docker ps >/dev/null 2>&1 || DK="sudo docker"
printf 'read_db /odb/%s\nsource /out/geom_dump.tcl\n' "$OB" > "$OUT/dump.tcl"
cp "$TOOLS/geom_dump.tcl" "$TOOLS/geom_grt.tcl" "$OUT/"
run() {  # name mem script log env...
  local nm=$1 mem=$2 sc=$3 lg=$4; shift 4
  local ev=(); for e in "$@"; do ev+=(-e "$e"); done
  $DK run --rm --name "ap-ageom-$ID-$nm-$$" --cpus 2 --memory "${mem}g" --memory-swap "${mem}g" -v "$OD":/odb:ro -v "$OUT":/out \
    -e HUID=$(id -u) -e HGID=$(id -g) "${ev[@]}" -w /out "$IMG" bash -lc \
    "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit $sc > $lg 2>&1; rc=\$?; chown -R \$HUID:\$HGID /out; exit \$rc"
}
GPID=""
if [ "$GRT" = true ]; then
  run grt "$MEM" /out/geom_grt.tcl /out/grt.log OT_GRT_ODB=/odb/$OB OT_GRT_MAX=$GMAX OT_GRT_MIN=$GMIN OT_GRT_ADJ=$GADJ \
      OT_GRT_ITER=$GITER OT_GRT_RPT=/out/cong.rpt &
  GPID=$!
fi
run dump "$MEM" /out/dump.tcl /out/dump.log OT_GEOM_OUT=/out/geom.tsv
rc=$?
tail -1 "$OUT/dump.log"
[ -n "$GPID" ] && { wait "$GPID"; echo "AP_AUTO_GEOM_GRT rc $? ($GMIN-$GMAX adj $GADJ, $GITER it)"; }
[ $rc = 0 ] || { echo "AP_AUTO_GEOM_ERROR dump rc $rc"; exit $rc; }
mapfile -t RA < <(python3 -I -c 'import json,sys;[print(a) for a in json.load(open(sys.argv[1])).get("rules_args",[])]' "$OUT/check.json")
GA=(); [ "$GRT" = true ] && GA=(--grt-log "$OUT/grt.log")
# Actual kit models classify synchronous memory boundaries; never infer them from names.
# OPT-IN (COORD 10-29): only when OT_GEOM_MEMORY_REACH=1; default keeps the flop-only r2r rule unchanged.
if [ "${OT_GEOM_MEMORY_REACH:-0}" = 1 ]; then
  GA+=(--memory-reach)
  while IFS= read -r -d '' ml; do GA+=(--memory-lib "$ml"); done < <(find "$KIT/macros" -type f \( -name '*.lib' -o -name '*.lib.gz' \) -print0 2>/dev/null)
fi
# Typed 12.2a1 die-owned arcs need BOTH matching metadata files and actual
# checkpoint connectivity; missing/invalid metadata grants no exemption.
if [ -f "$KIT/ft_interface.json" ] || [ -f "$KIT/ft_ports.json" ]; then
  GA+=(--ft-interface "$KIT/ft_interface.json" --ft-ports "$KIT/ft_ports.json")
fi
python3 -I "$TOOLS/geom_rules.py" "$OUT/geom.tsv" --odb "$ODB" --json "$OUT/auto_geom.json" --max-layer "$GMAX" "${GA[@]}" "${RA[@]}"
vrc=$?
PA=(); [ "$GRT" = true ] && PA=(--cong "$OUT/cong.rpt")
python3 -E "$TOOLS/geom_png.py" "$OUT/geom.tsv" "$OUT/auto_geom.json" "$OUT/auto_geom.png" "${PA[@]}" \
  >/dev/null 2>&1 && echo "AP_AUTO_GEOM_PNG $OUT/auto_geom.png" || echo "AP_AUTO_GEOM_PNG_ERROR"
exit $vrc
