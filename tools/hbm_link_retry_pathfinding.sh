#!/usr/bin/env bash
set -euo pipefail
out=$1
[[ "$out" = /* && ! -e "$out" ]]
mkdir -p "$out"
export OT_ORFS_NUM_CORES=16 OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
# RAM admission follows inventory16macros+smallcontrol, far below existing
# collective24GiB job.24GiB is reservation, not a process cap.
/srv/opentallas-scratch/admit.sh 24 -- python3 tools/run_abi3_physical_aligned_guarded.py \
 --macro-track-gate --view asap7 --top ot_hbm_link_retry_sram --param ENABLE=1 --param W=545 --param DEPTH=512 \
 --source rtl/common/ot_secded.sv \
 --source rtl/hbm_accel/tu/link_retry_sram_20261008/ot_hbm_replay_sram.sv \
 --source rtl/hbm_accel/tu/link_retry_sram_20261008/ot_hbm_link_retry_sram.sv \
 --macro-view ot_sram_1r1w_128x256_m1_r2c2=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2 \
 --macro-place-halo 4 4 --step-tcl MACRO_PLACEMENT=physical/hbm_link_retry_20261008/macro_place.tcl \
 --clock-period-ns .833333333 --clock-uncertainty-ns .06 --clock-uncertainty-hold-ns .025 \
 --orfs-corner WC --hold-corners WC,BC --io-delay-fraction .2 \
 --die-area 0 0 470 340 --core-area 5.4 5.4 464.6 334.6 \
 --stages synth,pnr --core-utilization 55 --place-density .55 \
 --hold-margin-ns .015 --orfs-var ADDER_MAP_FILE= --slew-margin-percent 30 \
 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
 --purpose characterization --nickname-tag hbm_retry545_pathfinding \
 --keep-workdir "$out/work" --output "$out/physical.json" > "$out/run.log" 2>&1
python3 tools/w18/corner_sta.py --orfs-dir "$out/work/orfs" --output "$out/corner_sta.json" > "$out/corner.log" 2>&1
