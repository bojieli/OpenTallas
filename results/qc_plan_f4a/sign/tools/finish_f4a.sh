#!/bin/bash
# QC-SU-F4A-SIGN 2026-10-26: after diagnostic DRT (5_2_route) -> fill + final (ORFS RCX 6_final.spef) + abstract + pin audit +
# corners.tcl TT/FF.  Clock untouched (12.8: no clock edits); no repair stage here.  usage: finish_f4a.sh KITDIR
set -uo pipefail
K=$(cd "$1" && pwd); TOP=$(sed -n "s/^export DESIGN_NAME = //p" "$K/config.mk")
grep -q "detailedroute__route__drc_errors\"\?: 0" $K/run/logs/asap7/*/base/5_2_route.json || { echo "DRT not clean"; exit 9; }
docker run --rm --name qcf4a-fin-$(basename $K)-$$ --cpus=8 --memory=24g --memory-swap=24g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; rc=0; M=\"make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8\"; for t in do-5_3_fillcell do-5_route do-5_route.sdc do-6_1_fill do-6_1_fill.sdc do-6_report do-generate_abstract; do \$M \$t || { rc=\$?; echo STAGE_FAIL \$t rc \$rc; break; }; done; \
 F=\$(ls /work/run/results/asap7/*/base/6_final.odb 2>/dev/null | tail -1); \
 if [ -n \"\$F\" ]; then ODB=\$F PINS=/work/pins.json OUT=/work/pin_audit.json openroad -python -exit /work/pin_audit.py > /work/pin_audit.log 2>&1; \
   for c in TT FF; do OT_CORNER=\$c DESIGN_NAME=$TOP ODB=\$F SPEF=\${F%.odb}.spef openroad -exit /work/corners.tcl > /work/sta_\$c.log 2>&1; done; fi; exit \$rc" > "$K/finish.log" 2>&1
rc=$?
docker run --rm -v "$K":/work openroad/orfs:asap7lock chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
echo "finish rc $rc $(date -Is)" >> "$K/finish.log"; exit $rc
