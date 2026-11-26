#!/bin/bash
# AUTOPILOT review bundle (read-only on the kit): dump the routed ODB (tools/ref_tile/layout_dump.tcl in the pinned ORFS
# image, kit mounted read-only) and draw floorplan/density + the failing sign-off paths (render_review.py); with review.json stage_paths
# (checkpoint renders, no sign-off yet) also the worst-50 setup + hold paths of the DB itself (stage_paths.tcl).
#   render_review.sh REVIEW_DIR      (REVIEW_DIR/review.json from autopilot.py, mem_gb = its ot-run --mem)
set -uo pipefail
REV=$(cd "$1" && pwd)
read -r KIT ODB IMG ID MEM SP < <(python3 -I -c 'import json,sys;d=json.load(open(sys.argv[1]));print(d["kit"],d["odb"],d["image"],d["id"],d.get("mem_gb",8),int(bool(d.get("stage_paths"))))' "$REV/review.json")
case "$ODB" in "$KIT"/*) REL=${ODB#"$KIT"/} ;; *) echo "AP_REVIEW_ERROR odb $ODB not inside kit $KIT"; exit 2 ;; esac
test -f "$ODB" || { echo "AP_REVIEW_ERROR routed ODB missing: $ODB"; exit 2; }
DK=docker; docker ps >/dev/null 2>&1 || DK="sudo docker"
printf 'read_db /kit/%s\nsource /rev/tools/layout_dump.tcl\n' "$REL" > "$REV/dump.tcl"
# stage_paths (SMELL / checkpoint renders, no sign-off STA yet): worst-50 setup + hold paths of this DB for the paths.png overlay
if [ "${SP:-0}" = 1 ] && [ -f "$REV/tools/stage_paths.tcl" ]; then
  printf 'set ::env(SP_ODB) /kit/%s\nset ::env(SP_OUT) /rev\nsource /rev/tools/stage_paths.tcl\n' "$REL" >> "$REV/dump.tcl"
fi
$DK run --rm --name "ap-render-$ID-$$" --cpus 2 --memory "${MEM}g" --memory-swap "${MEM}g" -v "$KIT":/kit:ro -v "$REV":/rev \
  -e HUID=$(id -u) -e HGID=$(id -g) -e OT_LAYOUT_OUT=/rev/layout.json -w /rev "$IMG" bash -lc \
  "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /rev/dump.tcl > /rev/dump.log 2>&1; rc=\$?; chown -R \$HUID:\$HGID /rev; exit \$rc"
rc=$?
tail -2 "$REV/dump.log"
python3 -I "$REV/tools/render_review.py" "$REV"
rc2=$?
[ $rc = 0 ] && exit $rc2 || exit $rc
