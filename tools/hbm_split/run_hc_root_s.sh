#!/bin/bash
# HBM-P5-RTLB 10-23: hc_root over-cap split INTEGRATION bench: the HC quarter-engine ring lock-step bench
# (rtl/test/run_hbm_hc_eng4_ring.sh: root + 4 x qeng vs the single-block golden, --split npos 1, every mix + every result
# word bit-exact) with the root replaced by ot_hbm_hc_root_static_s (tails on ot_hdc_sinkhorn_s, tail calendar +1 sink
# edge = +7 core edges) and the programme's emits moved by --tail-extra 7 (tail launch -> emit 497 -> 504).
# usage: run_hc_root_s.sh OUT [SMUT] [TAIL_EXTRA]   SMUT 1 (calendar not moved) must FAIL; TAIL_EXTRA 0 with SMUT 0 must FAIL.
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd); cd "$root"
out=$(realpath -m "${1:?OUT}"); smut=${2:-0}; tx=${3:-7}; mkdir -p "$out"
# HBM-P6-CMP 10-23: TAIL_EXTRA "LS" = take the compiler default (tools/hbm_static/leaf_split_latency.py hc_tail_result:
# 7 with OT_HBM_LEAF_SPLIT=1) instead of an explicit value: the gate gets no --tail-extra.
if [ "$tx" = LS ]; then txa=(); else txa=(--tail-extra "$tx"); fi
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x "$vl" ] || vl=verilator
H=rtl/hbm_accel/generic/peers/static_hc
sed -e 's/    ot_hbm_hc_root_static #(.MUT(MUTP),/    ot_hbm_hc_root_static_s #(.SMUT(`HC_SMUT), .MUT(MUTP),/' -e 's/^module tb_hbm_hc_eng4_static;/module tb_hbm_hc_eng4_static;  \/\/ HBM-P5-RTLB: root = ot_hbm_hc_root_static_s/' \
  rtl/test/tb_hbm_hc_eng4_static.sv > "$out/tb_hbm_hc_eng4_static_s.sv"
grep -q 'ot_hbm_hc_root_static_s #(.SMUT' "$out/tb_hbm_hc_eng4_static_s.sv"
src=("$out/tb_hbm_hc_eng4_static_s.sv" $H/ot_hbm_hc_root_static_s.sv $H/ot_hbm_hc_qeng_static.sv $H/ot_hbm_hc_qcen_static.sv
 $H/ot_hbm_hc_bankq_static.sv $H/ot_hbm_hc_eng_seq_static.sv $H/ot_hbm_hc_bank_static.sv $H/ot_hbm_hc_tail_unit_static_s.sv
 $H/ot_hdc_v41x_hcp_sys1_static.sv $H/ot_hgi_hc_tail_static_s.sv $H/ot_hbm_hc_xw_rx_static.sv
 rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv rtl/hdc/v41x/ot_hdc_v41x_hcp.sv rtl/hdc/ot_hdc_prefix.sv
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv
 rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/v41/ot_hdc_fdiv.sv
 rtl/hdc/v41/ot_hdc_sinkhorn_s.sv rtl/hdc/v41/ot_hdc_sk_arith.sv rtl/hdc/v41/ot_hdc_sk_recip_rom.sv rtl/lib/ot_rst_relay.sv
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v)
cpr=${HC_CPR:-1}; raw0=$((165 + 11 * cpr))
sha256sum "${src[@]}" "$0" tools/rtl_hbm_hc_eng_static_gate.py > "$out/sources.sha256"
python3 tools/rtl_hbm_hc_eng_static_gate.py --run "$out/case" --split --npos 1 --raw0 $raw0 --rs 104 "${txa[@]}" > "$out/vectors.log"
"$vl" --binary --timing --hierarchical -j "${HC_BUILD_JOBS:-16}" -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN \
  ${HC_VL_EXTRA:-} --top-module tb_hbm_hc_eng4_static +define+MUT=0 +define+HC_SMUT=$smut +define+HC_CPR=$cpr +define+OT_FP_DATA_NORST -Mdir "$out/obj" -o Vring \
  rtl/test/tb_hbm_hc_eng4_static_hier.vlt "${src[@]}" > "$out/build.log" 2>&1 || { tail -30 "$out/build.log"; exit 3; }
set +e; (cd "$out/case" && "$out/obj/Vring" $(cat plus.txt)) > "$out/run.log" 2>&1; rc=$?; set -e
# negative control on the same binary: the programme with emits NOT moved (tail launch + 497) must FAIL
if [ "$smut" = 0 ] && [ "$tx" != 0 ]; then
 python3 tools/rtl_hbm_hc_eng_static_gate.py --run "$out/case_neg" --split --npos 1 --raw0 $raw0 --rs 104 --tail-extra 0 > "$out/vectors_neg.log"
 set +e; (cd "$out/case_neg" && "$out/obj/Vring" $(cat plus.txt)) > "$out/run_neg.log" 2>&1; rcn=$?; set -e
 grep -E "HC_ENG_DONE|HC_ENG PASS|HC_ENG FAIL|FAULT" "$out/run_neg.log" | head -3; echo "HC_ROOT_S NEG (emit +0) rc=$rcn (must be non-zero)"
fi
grep -E "HC_ENG_DONE|HC_ENG PASS|HC_ENG FAIL|FAULT" "$out/run.log" | head -4
echo "HC_ROOT_S SMUT=$smut TAIL_EXTRA=$tx rc=$rc (CPR=$cpr RAW0=$raw0)"
rm -rf "$out/obj"
exit $rc
