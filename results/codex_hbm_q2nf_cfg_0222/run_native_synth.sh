#!/bin/bash
set -euo pipefail
K=$1
DK=docker
$DK ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --name codex-q2nf-cfg-synth-0222 --memory=32g --memory-swap=32g --cpus=8 -e OT_LEC_REPLICA_MATCH=1 -e OT_LEC_PARITY_TERMS=1024 -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
set -euo pipefail
trap '\''rc=$?;chown -R 1000:1000 /work;exit $rc'\'' EXIT
if grep -q "^override export OT_HOLD_MM = 1" /work/config.mk;then python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.log 2>&1;fi
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 synth > /work/run_native_synth.log 2>&1
python3 -I /work/lec.py /work --out /work/lec_native > /work/lec_native.log 2>&1
printf "%s\n" "Native synth/LEC done; no physical stage released" > /work/SYNTH_DONE.txt
'
