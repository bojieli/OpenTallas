#!/usr/bin/env bash
# Necessary bounded actual four-stop transport proof, F12 dense and F16 3-source.
# VM boundary data tests transport only; does not qualify remote SU producers.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=$(realpath -m "$1"); mkdir -p "$OUT"; cd "$ROOT"
V=${VERILATOR:-verilator}
P=rtl/hbm_accel/generic/collective/p2p
LIB=("$P/ot_hgi_coll_gq.sv" "$P/ot_hgi_coll_ring_ag.sv" "$P/ot_hgi_coll_ring_ag_lane.sv" "$P/ot_hgi_coll_ring_b_stop.sv"
     "$P/ot_hgi_coll_pring_static_state_capture.sv" "$P/ot_hgi_coll_pring_static.sv"
     rtl/hbm_accel/index/quad_1017/ot_hbm_idx_vm_share2_static.sv rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv
     rtl/lib/ot_rst_relay.sv physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_tree13.sv physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_scale13.sv
     rtl/hdc/v41/ot_hdc_actquant.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_delay.sv
     rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv)
FL=(--binary --timing -O2 -j "${JOBS:-16}" -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-MULTITOP -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN)
for f in 12 16; do
 "$V" "${FL[@]}" -DOT_COLL_GQ_SINGLE_SENDER -GWAVE_F=$f -GLANES=1 -GVM_RT=74 -GBANK_RT=72 --top-module tb_hgi_coll_gq_wave --Mdir "$OUT/f$f" "$P/tb_hgi_coll_gq_wave.sv" "${LIB[@]}" > "$OUT/f$f.build.log" 2>&1
 "$OUT/f$f/Vtb_hgi_coll_gq_wave" > "$OUT/f$f.run.log" 2>&1
 tail -4 "$OUT/f$f.run.log"
 grep -q '^COLLQ WAVE PASS ' "$OUT/f$f.run.log"
done
"$OUT/f12/Vtb_hgi_coll_gq_wave" +fault=4 > "$OUT/f12.drop.log" 2>&1
grep '^COLLQ FAULT PASS scenario=4' "$OUT/f12.drop.log"
echo 'COLLQ WAVE SOURCE PASS F12four/F16three actualVM/ringA+B/landing; missing-transit causal PASS'
