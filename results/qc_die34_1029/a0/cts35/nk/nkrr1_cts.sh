#!/bin/bash
# DIE-QC-35 (A0): CTS on the GEOM-59 PASS-COND 3_place, NO re-place (make -n cts = do-4_1_cts + do-4_cts only, checked).
# Same docker pattern as nkrr1_place.sh; orfs_hold_mm patch applied as run_kit.sh does (OT_HOLD_MM=1) before make cts.
set -euo pipefail
k=/srv/opentallas-scratch2/claude/die-qc34-a0/kits/qfd_tile_nk_a0c_a0nk14icg2rr1
sudo docker run --rm --name dqc35-a0-nkrr1-cts --cpus=8 --memory=32g --memory-swap=32g -v "$k":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
set -euo pipefail
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.log 2>&1
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 cts
" > "$k/cts.log" 2>&1
