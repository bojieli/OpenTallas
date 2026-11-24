#!/bin/bash
# sender_margin_probe.sh KIT_DIR OUT_DIR   read-only, TT single corner (CORNERS cleared even for tc/bc kits); run under ot-run.
# Output: OUT_DIR/sender.tsv (see sender_margin_probe.tcl). SMP_DRY=1 prints the command.
set -euo pipefail
K=$(readlink -f "$1"); mkdir -p "$2"; O=$(readlink -f "$2"); here=$(cd "$(dirname "$0")" && pwd)
odb=$(ls "$K"/run/results/asap7/*/base/4_cts.odb | head -1); sdc=$(dirname "$odb")/4_cts.sdc
[ -s "$sdc" ] || { echo "no 4_cts.sdc next to $odb" >&2; exit 2; }
nick=$(basename "$(dirname "$(dirname "$odb")")")
cp "$here/sender_margin_probe.tcl" "$O/smp.tcl"
run="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=4 LOG_DIR=/out/logs OBJECTS_DIR=/work/run/objects/asap7/$nick/base CORNERS= RUN_SCRIPT=/out/smp.tcl run"
if [ -n "${SMP_DRY:-}" ]; then echo "$run"; exit 0; fi
rm -f "$O/sender.tsv"
docker run --rm --name "smp-$$" --cpus=4 --memory=60g -e VIS_ODB=4_cts.odb -e VIS_SDC=4_cts.sdc -e SMP_OUT=/out/sender.tsv \
  -v "$K":/work:ro -v "$O":/out -w /OpenROAD-flow-scripts/flow "${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}" \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; $run; rc=\$?; chown -R $(id -u):$(id -g) /out; exit \$rc" > "$O/run.log" 2>&1 || { tail -5 "$O/run.log"; exit 1; }
grep -a "SMP_DONE" "$O/run.log"
[ -s "$O/sender.tsv" ]
