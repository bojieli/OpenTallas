#!/bin/bash
set -euo pipefail
K=/srv/opentallas-scratch2/claude/codex-kv-hr-1030/phy103_zero_cts1
sudo docker run --rm --name codex-kvhr1030-phy103-cts1 --cpus 4 --memory 16g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
set -e
trap "chown -R 1000:1000 /work" EXIT
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/cts_patch.log 2>&1
R=/work/run/results/asap7/hc_qkd_hr_phy_adp__103_68x95_04/base
make -o "$R/3_place.odb" -o "$R/3_place.sdc" DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=4 SKIP_CTS_REPAIR_TIMING=1 cts
' > "$K/cts_screen.log" 2>&1
