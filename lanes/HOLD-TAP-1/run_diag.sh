#!/bin/bash
# usage: run_diag.sh KIT OUTDIR [odb-stage default 4_cts]  -- read-only FF hold classification (docker, STA only)
set -euo pipefail
K=$1; mkdir -p $2; O=$(realpath $2); ST=${3:-4_cts}
B=$(ls -d $K/run/results/asap7/*/base | head -1)
cp /srv/opentallas-scratch2/claude/hold-tap-1/diag/xtap_diag.tcl $O/
LP=$(sed -n 's/^export LAYER_PARASITICS_FILE = //p' $K/config.mk)
docker run --rm --name ht1_diag_$$ --cpus=16 --memory=64g -v $K:/work:ro -v $O:/out -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base'; PLIBS=\"\$(\$M print-BC_LIB_FILES 2>/dev/null | sed -n 's/^BC_LIB_FILES *[:=] *//p')\" ODB=/work/run/results/asap7/$(basename $(dirname $B))/base/$ST.odb SDC=/work/run/results/asap7/$(basename $(dirname $B))/base/4_cts.sdc PLATFORM_DIR=/OpenROAD-flow-scripts/flow/platforms/asap7 LAYER_PARASITICS_FILE='$LP' OUT=/out/xtap.tsv SLACK_MAX=${SLACK_MAX:-0} openroad -no_init -exit /out/xtap_diag.tcl" > $O/diag.log 2>&1
tail -2 $O/diag.log
