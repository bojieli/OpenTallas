#!/bin/bash
# DIE-QC-36 A0: CTS with the plan-built tile tree (core_infra opt-in delta, install_stage pre_cts) on a COPY of the
# GEOM PASS-COND 3_place, NO re-place: refuses unless `make -n cts` = do-4_1_cts + do-4_cts only.
# Same docker pattern as die-qc34-a0 cts36/n?_b_cts.sh; orfs_hold_mm patch as run_kit.sh does (OT_HOLD_MM=1).
set -euo pipefail
k=$1; name=$2
sudo docker run --rm --name "$name" --cpus=8 --memory=24g --memory-swap=24g -v "$k":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
set -euo pipefail
make -n DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 cts | grep -oE \"do-[0-9a-z_]+\" | sort -u > /work/make_n_cts.txt
if grep -vqE \"^do-4_(1_)?cts\$\" /work/make_n_cts.txt; then echo REFUSE_RERUN; cat /work/make_n_cts.txt; exit 3; fi
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.log 2>&1
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 cts
" > "$k/cts.log" 2>&1
