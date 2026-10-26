#!/bin/bash
# AUTO-GEOM rule check (read-only on the kit): dump a placed / CTS ODB with geom_dump.tcl in the pinned ORFS image
# (ODB dir mounted read-only) and judge it with geom_rules.py.
#   geom_check.sh OUTDIR        OUTDIR/check.json = {"odb", "image", "id", "mem_gb", "rules_args": [...]} from autopilot.py
# Writes OUTDIR/geom.tsv (dump), OUTDIR/auto_geom.json (rule results), prints "AP_AUTO_GEOM <verdict line>".
set -uo pipefail
OUT=$(cd "$1" && pwd)
TOOLS=$(cd "$(dirname "$0")" && pwd)
read -r ODB IMG ID MEM < <(python3 -I -c 'import json,sys;d=json.load(open(sys.argv[1]));print(d["odb"],d.get("image","openroad/orfs:asap7lock"),d["id"],d.get("mem_gb",8))' "$OUT/check.json")
test -f "$ODB" || { echo "AP_AUTO_GEOM_ERROR checkpoint missing: $ODB"; exit 2; }
OD=$(dirname "$ODB"); OB=$(basename "$ODB")
DK=docker; docker ps >/dev/null 2>&1 || DK="sudo docker"
printf 'read_db /odb/%s\nsource /out/geom_dump.tcl\n' "$OB" > "$OUT/dump.tcl"
cp "$TOOLS/geom_dump.tcl" "$OUT/geom_dump.tcl"
$DK run --rm --name "ap-ageom-$ID-$$" --cpus 2 --memory "${MEM}g" --memory-swap "${MEM}g" -v "$OD":/odb:ro -v "$OUT":/out \
  -e HUID=$(id -u) -e HGID=$(id -g) -e OT_GEOM_OUT=/out/geom.tsv -w /out "$IMG" bash -lc \
  "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /out/dump.tcl > /out/dump.log 2>&1; rc=\$?; chown -R \$HUID:\$HGID /out; exit \$rc"
rc=$?
tail -1 "$OUT/dump.log"
[ $rc = 0 ] || { echo "AP_AUTO_GEOM_ERROR dump rc $rc"; exit $rc; }
mapfile -t RA < <(python3 -I -c 'import json,sys;[print(a) for a in json.load(open(sys.argv[1])).get("rules_args",[])]' "$OUT/check.json")
python3 -I "$TOOLS/geom_rules.py" "$OUT/geom.tsv" --odb "$ODB" --json "$OUT/auto_geom.json" "${RA[@]}"
