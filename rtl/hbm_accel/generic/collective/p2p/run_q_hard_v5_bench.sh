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
src=("$p/tb_hgi_coll_q_hard_v5.sv" "$p/ot_hfd_coll_q_hard_v5.sv" "$p/ot_hgi_coll_ctl_v5.sv" "$p/ot_hfd_coll_q3_static_host_v4.sv"
 "$p/ot_hfd_coll_q2_static_host_v4.sv" "$p/ot_hgi_coll_static_program_target.sv" "$p/ot_hfd_coll_q_static_v4.sv"
 "$p/ot_hgi_coll_static_issuer.sv" "$p/ot_hgi_coll_static_issuer_v5.sv" "$p/ot_hgi_coll_static_issuer_v6.sv" "$p/ot_hgi_coll_qslots.sv" "$p/ot_hgi_coll_qslots_capture_pin_v2.sv"
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
QD=(); [ "$Q" = q3 ] && QD=(-DQ3 --hierarchical "$p/qhard_hier.vlt")
# q3 elaborates two KMAX-2048 TKMs (host_v4 ref + hard_v5): -j16 hierarchical OOMs 128 GB (EPYC4 oom-kill) and -j4
# outlives the closure-loop bench timeout (ctl3 7d6120e84: SIGTERM after 80 min). No q3 scenario starts the TKM
# (scen3 is q2-only; q3 programme rows never set p_tkm_start), so by default BOTH parents get the same KMAX-64 copy of
# ot_hgi_coll_tkm_static (one tile; identical ports/edges, generated here, hashed in sources.sha256). The KMAX-2048
# TKM is qualified by its own leaf benches. HCOLL_Q3_FULL_TKM=1 restores the production KMAX (needs ~230 GB -j1).
if [ "$Q" = q3 ] && [ "${HCOLL_Q3_FULL_TKM:-0}" != 1 ]; then
 sed 's/parameter integer KMAX=2048/parameter integer KMAX=64/' "$t/ot_hgi_coll_tkm_static.sv" > "$OUT/ot_hgi_coll_tkm_static_k64.sv"
 grep -q 'parameter integer KMAX=64' "$OUT/ot_hgi_coll_tkm_static_k64.sv" || { echo "KMAX64 copy failed"; exit 2; }
 for i in "${!src[@]}"; do [ "${src[$i]}" = "$t/ot_hgi_coll_tkm_static.sv" ] && src[$i]="$OUT/ot_hgi_coll_tkm_static_k64.sv"; done
 echo "HCOLL_Q3_TKM_KMAX64 (bench copy; production TKM unchanged)"
 JOBS=${JOBS_Q3:-8}
fi
sha256sum "${src[@]}" > "$OUT/sources.sha256"
[ "$Q" = q3 ] && JOBS=${JOBS:-${JOBS_Q3:-4}}
build(){ # name defines...
 local n=$1; shift
 "$V" --binary --timing -j "${JOBS:-16}" -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT \
  --top-module tb_hgi_coll_q_hard_v5 "${QD[@]}" "$@" -Mdir "$OUT/obj_$n" "${src[@]}" > "$OUT/$n.build.log" 2>&1 \
  || { tail -30 "$OUT/$n.build.log"; exit 2; }
}
vmsel_witness(){
 # A crash or failed build cannot qualify this negative: require the actual swapped-payload observation.
 ! grep -q '^HCOLL_Q_HARD_V5 PASS' "$1" &&
 grep -Eq '^MISMATCH .*dd_eq0' "$1" &&
 grep -Eq 'lockstep: [1-9][0-9]* cycles with a non-fault output difference' "$1"
}
run(){ # name scen expect
 local n=$1 s=$2 e=$3 rc
 sha256sum "$OUT/obj_$n/Vtb_hgi_coll_q_hard_v5" > "$OUT/${n}.compiled.sha256"
 set +e; "$OUT/obj_$n/Vtb_hgi_coll_q_hard_v5" +SCEN=$s > "$OUT/${n}_s$s.log" 2>&1; rc=$?; set -e
 grep -E 'HCOLL_Q_HARD_V5|MISMATCH|Fatal|fatal' "$OUT/${n}_s$s.log" | head -4
 if [ "$e" = pass ]; then { [ $rc = 0 ] && grep -q '^HCOLL_Q_HARD_V5 PASS' "$OUT/${n}_s$s.log"; } || { echo "POSITIVE $n scen$s FAILED"; fail=1; }
 else
  if [ $rc != 0 ] && ! grep -q '^HCOLL_Q_HARD_V5 PASS' "$OUT/${n}_s$s.log" &&
     { [ "$n" != mut_vmsel ] || vmsel_witness "$OUT/${n}_s$s.log"; }; then
   echo "MUTANT $n scen$s rejected"
  else echo "MUTANT $n scen$s SURVIVED_OR_NO_WITNESS"; fail=1; fi
 fi
}
fail=0
declare -A MS=([droplink]="OT_COLL_V5_MUT_DROP_LINK 1" [nomask]="OT_COLL_V5_MUT_NOMASK 0" [causeswap]="OT_COLL_V5_MUT_CAUSE_SWAP 4" [droptkm]="OT_COLL_V5_MUT_DROP_TKM 3" [vmsel]="OT_COLL_V6_MUT_VMSEL 7" [obsnoalign]="OT_COLL_V7_MUT_OBS_NOALIGN 7" [rcdrop]="OT_COLL_V7_MUT_RCDROP 2")
if [ "$MODE" != all ] && [ "$MODE" != pos ] && [ "$MODE" != vmpos ]; then
 set -- ${MS[$MODE]:?unknown mode $MODE}
 build "m_$MODE" -D$1; run "m_$MODE" $2 pass; rm -rf "$OUT/obj_m_$MODE"
 if [ "$MODE" = vmsel ] && [ "$fail" != 0 ] && ! vmsel_witness "$OUT/m_vmsel_s$2.log"; then
  echo "HCOLL_Q_HARD_V5_MUTANT_INVALID vmsel missing swapped-payload witness"; exit 2
 fi
 [ $fail = 0 ] && { echo "HCOLL_Q_HARD_V5_MUTANT_SURVIVED $MODE"; exit 0; } || { echo "HCOLL_Q_HARD_V5_MUTANT_REJECTED $MODE"; exit 1; }
fi
build base
if [ "$Q" = q3 ]; then SC="0 1 2 4 6 7"; else SC="0 1 2 3 4 5 6 7"; fi
[ "$MODE" = vmpos ] && SC="7"
for s in $SC; do run base $s pass; done
if [ "$MODE" = pos ] || [ "$MODE" = vmpos ]; then [ $fail = 0 ] && { echo "HCOLL_Q_HARD_V5_POS_PASS $Q"; exit 0; } || { echo "HCOLL_Q_HARD_V5_POS_FAIL $Q"; exit 1; }; fi
build mut_droplink -DOT_COLL_V5_MUT_DROP_LINK; run mut_droplink 1 fail
build mut_nomask -DOT_COLL_V5_MUT_NOMASK; run mut_nomask 0 fail
build mut_vmsel -DOT_COLL_V6_MUT_VMSEL; run mut_vmsel 7 fail
build mut_causeswap -DOT_COLL_V5_MUT_CAUSE_SWAP; run mut_causeswap 4 fail
build mut_obsnoalign -DOT_COLL_V7_MUT_OBS_NOALIGN; run mut_obsnoalign 7 fail
build mut_rcdrop -DOT_COLL_V7_MUT_RCDROP; run mut_rcdrop 2 fail
if [ "$Q" = q2 ]; then build mut_droptkm -DOT_COLL_V5_MUT_DROP_TKM; run mut_droptkm 3 fail; fi
rm -rf "$OUT"/obj_mut_*
[ $fail = 0 ] && echo "HCOLL_Q_HARD_V5_GATE_PASS $Q" || { echo "HCOLL_Q_HARD_V5_GATE_FAIL $Q"; exit 1; }
