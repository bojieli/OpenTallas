#!/bin/bash
set -euo pipefail
out=${1:?};mkdir -p "$out"
readset=results/arch/hbm_col8_parent_1021/residual_sources.txt
args=(); sources=(); while IFS= read -r p; do
 if [[ "$p" == rtl/hdc/v41x/ot_hidx_meta_sram146.sv ]]; then p=rtl/hdc/v41x/col8_parent_1021/meta_hard_interface.v; fi
 sources+=("$p"); args+=(--source "$p");
done < "$readset"
sha256sum "$readset" "${sources[@]}" > "$out/source_receipt.txt"
export OT_ORFS_NUM_CORES=8 OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
python3 tools/run_abi3_physical.py --view asap7 --top ot_hbm_idx_score_quarter_col8_control --param TP=192 "${args[@]}" --clock-port clk_ctl --clock-period-ns 0.833333 --stages pnr --pnr-stop-after floorplan --die-area 0 0 3456 2160 --core-area 2.16 2.16 3453.84 2157.84 --macro-view ot_hidx_meta_sram146=physical/ref_tile/hidx_meta146_main_1021/views/ot_hidx_meta_sram146 --macro-place-halo 5.4 5.4 --orfs-corner WC --hold-corners WC,BC --routing-layers M2 M5 --step-tcl PRE_FLOORPLAN=results/arch/hbm_col8_parent_1021/native_map_only.tcl --orfs-var OT_NATIVE_KIT=hidx_quarter_control_hardmeta_native_1021 --orfs-var NUM_CORES=8 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited --keep-workdir "$out/work" --output "$out/physical.json" > "$out/flow.log" 2>&1
