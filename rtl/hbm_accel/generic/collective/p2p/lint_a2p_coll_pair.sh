#!/usr/bin/env bash
# H-NETLIST A2P 2026-10-16: elaborate + lint the A2P half-die COLL pair exactly as the die binds it:
# hb_coll_SW = ot_hfd_coll_q3_static_host_v4 #(QID 0, N_Q 2), hb_coll_NW = ot_hfd_coll_q2_static_host_v4 #(QID 2, N_Q 2),
# ring SW.pr_cw_o -> NW.pr_cw_i, NW.pr_cw_o -> SW.pr_cw_i, SW.pr_ccw_o -> NW.pr_ccw_i, NW.pr_ccw_o -> SW.pr_ccw_i (280 b each).
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd); cd "$ROOT"
V=${VERILATOR:-verilator}; p=rtl/hbm_accel/generic/collective/p2p; t=rtl/hbm_accel/generic/collective/tkm
OUT=$(realpath -m "${1:-/tmp/a2p_coll_lint}"); mkdir -p "$OUT"
cat > "$OUT/a2p_coll_pair.sv" <<'SV'
module a2p_coll_pair(input wire rst_n, input wire clk);
 wire [279:0] sw_cw,sw_ccw,nw_cw,nw_ccw;
 ot_hfd_coll_q3_static_host_v4 #(.QID(2'd0),.N_Q(2)) u_sw(.rst_n(rst_n),.pr_cw_i(nw_cw),.pr_ccw_i(nw_ccw),.pr_cw_o(sw_cw),.pr_ccw_o(sw_ccw));
 ot_hfd_coll_q2_static_host_v4 #(.QID(2'd2),.N_Q(2)) u_nw(.rst_n(rst_n),.pr_cw_i(sw_cw),.pr_ccw_i(sw_ccw),.pr_cw_o(nw_cw),.pr_ccw_o(nw_ccw));
endmodule
SV
src=("$OUT/a2p_coll_pair.sv" "$p/ot_hfd_coll_q3_static_host_v4.sv" "$p/ot_hfd_coll_q2_static_host_v4.sv"
 "$p/ot_hgi_coll_static_program_target.sv" "$p/ot_hfd_coll_q_static_v4.sv" "$p/ot_hgi_coll_static_issuer.sv"
 "$p/ot_hgi_coll_qslots.sv" "$p/ot_hgi_coll_pring_static.sv" "$p/ot_hgi_coll_pring_captured_static.sv"
 "$p/ot_hgi_coll_pring_static_state_capture.sv" "$p/ot_hgi_coll_reduce_static.sv" "$p/ot_hgi_coll_argmax_static.sv"
 rtl/hbm_accel/generic/collective/ot_hgi_coll_amerge.sv "$t/ot_hgi_coll_tkm_static.sv" "$t/ot_hgi_coll_tkm.sv" "$t/ot_hgi_coll_tkm_buffer.sv"
 "$p/ot_hgi_coll_static_vmwrite.sv" "$p/ot_hgi_coll_static_link_capture.sv" "$p/ot_hgi_coll_static_capture_ctl.sv"
 "$p/ot_hgi_coll_static_pinreg_ctl.sv" "$p/ot_hgi_coll_static_pinreg_store.sv" "$p/ot_hgi_coll_static_seq_ctl.sv"
 rtl/lib/ot_rst_relay.sv rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv
 physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
"$V" --lint-only --hierarchical "$p/qtkm_hier.vlt" --timing -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-TIMESCALEMOD -Wno-PINMISSING -Wno-PINCONNECTEMPTY \
  --top-module a2p_coll_pair "${src[@]}" > "$OUT/lint.log" 2>&1 || { tail -20 "$OUT/lint.log"; echo A2P_COLL_PAIR_LINT FAIL; exit 1; }
grep -E '%Error' "$OUT/lint.log" && { echo A2P_COLL_PAIR_LINT FAIL; exit 1; }
echo A2P_COLL_PAIR_LINT PASS
