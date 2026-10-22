#!/bin/bash
set -euo pipefail
out=${1:?};mkdir -p "$out"
args=();while IFS= read -r p;do args+=(--source "$p");done < ../residual_sources.txt
sha256sum ../residual_sources.txt "${args[@]/--source/}" 2>/dev/null > "$out/source_receipt.txt" || true
export OT_ORFS_NUM_CORES=8 OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
python3 tools/run_abi3_physical.py --view asap7 --top ot_hbm_idx_score_quarter_col8_control --param TP=192 "${args[@]}" --clock-port clk_ctl --clock-period-ns 0.833333 --stages pnr --pnr-stop-after floorplan --die-area 0 0 3456 2160 --core-area 2.16 2.16 3453.84 2157.84 --macro-view ot_sram_1r1w_256x256_m2_r2c2=physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2 --macro-place-halo 5.4 5.4 --orfs-corner WC --hold-corners WC,BC --routing-layers M2 M5 --step-tcl PRE_FLOORPLAN=tools/ref_tile/native_census.tcl --orfs-var OT_NATIVE_KIT=hidx_quarter_control_native_1021 --orfs-var NUM_CORES=8 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited --keep-workdir "$out/work" --output "$out/physical.json" > "$out/flow.log" 2>&1
