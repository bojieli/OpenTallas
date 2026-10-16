#!/usr/bin/env bash
# H-NETLIST/COLL 1045: hard-hierarchy COLL quadrant lockstep + aggregate fault ABI gate (Verilator 5.050).
#   run_q_hard_v5_bench.sh OUT [q2|q3] [all|pos|droplink|nomask|causeswap|droptkm]
# pos = positive scenarios only (exit 0 on PASS); a mutant name = that mutant only, run as a POSITIVE claim (exit
# non-zero when the mutant is correctly rejected, i.e. a loop bench with expect "fail"); all = gate (default).
# Positive: every scenario PASSes (lockstep identical non-fault outputs every cycle; documented fault edge delta;
# fault_cause names the child). Mutants (each must FAIL): DROP_LINK (scen1), DROP_TKM (q2 scen3), NOMASK (scen0),
# CAUSE_SWAP (scen4).
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=${HCOLL_ROOT:-$(cd "$HERE/../../../../.." && pwd)}
OUT=$(realpath -m "${1:?output directory}"); Q=${2:-q2}; MODE=${3:-all}; mkdir -p "$OUT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; [ -x "$V" ] || V=verilator
p=$ROOT/rtl/hbm_accel/generic/collective/p2p; t=$ROOT/rtl/hbm_accel/generic/collective/tkm
src=("$p/tb_hgi_coll_q_hard_v5.sv" "$p/ot_hfd_coll_q_hard_v5.sv" "$p/ot_hfd_coll_q3_static_host_v4.sv"
 "$p/ot_hfd_coll_q2_static_host_v4.sv" "$p/ot_hgi_coll_static_program_target.sv" "$p/ot_hfd_coll_q_static_v4.sv"
 "$p/ot_hgi_coll_static_issuer.sv" "$p/ot_hgi_coll_qslots.sv" "$p/ot_hgi_coll_qslots_capture_pin_v2.sv"
 "$p/ot_hgi_coll_pring_static.sv" "$p/ot_hgi_coll_pring_captured_static.sv" "$p/ot_hgi_coll_pring_static_state_capture.sv"
 "$p/ot_hgi_coll_reduce_static.sv" "$p/ot_hgi_coll_argmax_static.sv" "$ROOT/rtl/hbm_accel/generic/collective/ot_hgi_coll_amerge.sv"
 "$p/ot_hgi_coll_static_vmwrite.sv" "$p/ot_hgi_coll_static_vmwrite_roots_v6_physical.sv" "$p/ot_hgi_coll_static_vmwrite_roots_v6.sv"
 "$p/ot_hgi_coll_static_link_capture.sv" "$p/ot_hgi_coll_static_capture_ctl.sv" "$p/ot_hgi_coll_static_pinreg_ctl.sv"
 "$p/ot_hgi_coll_static_pinreg_store.sv" "$p/ot_hgi_coll_static_seq_ctl.sv"
 "$t/ot_hgi_coll_tkm_static.sv" "$t/ot_hgi_coll_tkm.sv" "$t/ot_hgi_coll_tkm_buffer.sv" "$ROOT/rtl/lib/ot_rst_relay.sv"
 "$ROOT/rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv" "$ROOT/rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv"
 "$ROOT/rtl/hdc/ot_hdc_fp32_add_lat.sv" "$ROOT/rtl/hdc/ot_hdc_prefix.sv" "$ROOT/rtl/hdc/ot_hdc_fastfp.sv"
 "$ROOT/physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v"
 "$ROOT/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v")
sha256sum "${src[@]}" > "$OUT/sources.sha256"
QD=(); [ "$Q" = q3 ] && QD=(-DQ3 --hierarchical "$p/qtkm_hier.vlt")
build(){ # name defines...
 local n=$1; shift
 "$V" --binary --timing -j "${JOBS:-16}" -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT \
  --top-module tb_hgi_coll_q_hard_v5 "${QD[@]}" "$@" -Mdir "$OUT/obj_$n" "${src[@]}" > "$OUT/$n.build.log" 2>&1 \
  || { tail -30 "$OUT/$n.build.log"; exit 2; }
}
run(){ # name scen expect
 local n=$1 s=$2 e=$3 rc
 set +e; "$OUT/obj_$n/Vtb_hgi_coll_q_hard_v5" +SCEN=$s > "$OUT/${n}_s$s.log" 2>&1; rc=$?; set -e
 grep -E 'HCOLL_Q_HARD_V5|MISMATCH|Fatal|fatal' "$OUT/${n}_s$s.log" | head -4
 if [ "$e" = pass ]; then { [ $rc = 0 ] && grep -q '^HCOLL_Q_HARD_V5 PASS' "$OUT/${n}_s$s.log"; } || { echo "POSITIVE $n scen$s FAILED"; fail=1; }
 else { [ $rc != 0 ] && ! grep -q '^HCOLL_Q_HARD_V5 PASS' "$OUT/${n}_s$s.log"; } && echo "MUTANT $n scen$s rejected" || { echo "MUTANT $n scen$s SURVIVED"; fail=1; }; fi
}
fail=0
declare -A MS=([droplink]="OT_COLL_V5_MUT_DROP_LINK 1" [nomask]="OT_COLL_V5_MUT_NOMASK 0" [causeswap]="OT_COLL_V5_MUT_CAUSE_SWAP 4" [droptkm]="OT_COLL_V5_MUT_DROP_TKM 3")
if [ "$MODE" != all ] && [ "$MODE" != pos ]; then
 set -- ${MS[$MODE]:?unknown mode $MODE}
 build "m_$MODE" -D$1; run "m_$MODE" $2 pass; rm -rf "$OUT/obj_m_$MODE"
 [ $fail = 0 ] && { echo "HCOLL_Q_HARD_V5_MUTANT_SURVIVED $MODE"; exit 0; } || { echo "HCOLL_Q_HARD_V5_MUTANT_REJECTED $MODE"; exit 1; }
fi
build base
if [ "$Q" = q3 ]; then SC="0 1 2 4 6"; else SC="0 1 2 3 4 5 6"; fi
for s in $SC; do run base $s pass; done
if [ "$MODE" = pos ]; then [ $fail = 0 ] && { echo "HCOLL_Q_HARD_V5_POS_PASS $Q"; exit 0; } || { echo "HCOLL_Q_HARD_V5_POS_FAIL $Q"; exit 1; }; fi
build mut_droplink -DOT_COLL_V5_MUT_DROP_LINK; run mut_droplink 1 fail
build mut_nomask -DOT_COLL_V5_MUT_NOMASK; run mut_nomask 0 fail
build mut_causeswap -DOT_COLL_V5_MUT_CAUSE_SWAP; run mut_causeswap 4 fail
if [ "$Q" = q2 ]; then build mut_droptkm -DOT_COLL_V5_MUT_DROP_TKM; run mut_droptkm 3 fail; fi
rm -rf "$OUT"/obj_mut_*
[ $fail = 0 ] && echo "HCOLL_Q_HARD_V5_GATE_PASS $Q" || { echo "HCOLL_Q_HARD_V5_GATE_FAIL $Q"; exit 1; }
