#!/bin/bash
# DIE-QC-35 (A0) round 2, diag (B2, -no_insertion_delay): CTS with -delay_buffer_derate 0 on a COPY of the GEOM PASS-COND 3_place kit, NO re-place.
# Same docker pattern as die-qc34-a0/nkrr*_cts.sh; refuses if make -n cts would rerun anything before 4_1_cts.
set -euo pipefail
k=/srv/opentallas-scratch2/claude/die-qc34-a0/cts36b2/qfd_tile_nk_a0c_a0nk14icg2rr1
sudo docker run --rm --name dqc36-a0-nk-b2cts --cpus=8 --memory=16g --memory-swap=16g -v "$k":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
set -euo pipefail
make -n DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 cts | grep -oE \"do-[0-9a-z_]+\" | sort -u > /work/make_n_cts.txt
if grep -vqE \"^do-4_(1_)?cts\$\" /work/make_n_cts.txt; then echo REFUSE_RERUN; cat /work/make_n_cts.txt; exit 3; fi
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.log 2>&1
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 cts
" > "$k/cts.log" 2>&1
