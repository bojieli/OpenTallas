#!/bin/bash
# S81-PINREG4 bench runner: tb_qxpq_cpr (CPR=1 vs closed CPR=0 q element, both RSTP=1, routed params) -- pass + 3 mutants
# (copy of qxpq_rstp_bench.sh).
#   qxpq_cpr_bench.sh SRC_ROOT WORK [MODE]   (SRC_ROOT = source tree with rtl/ and tools/; ROMs = the tb fixtures)
#   MODE all (default): pass x3 seeds + both mutants; pass: positive run only (BENCH_RC 0 on PASS);
#   mut_go | mut_busy | mut_late: one mutant, prints MUTANT_DETECTED and exits 1 when the bench FAILs it (closure-loop expect=fail)
set -u
S=$(cd "$1" && pwd); W=$2; mkdir -p "$W"; W=$(cd "$W" && pwd)
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
TB=$S/tools/dsrom_qelem_cl/tb_qxpq_cpr.sv
RTL="rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10.sv rtl/v41rom/ot_v41_rom_elem_qx_pq_w10.sv rtl/v41rom/ot_v41_elem_pq_tags.sv rtl/v41rom/ot_v41_kreg.sv rtl/v41rom/ot_v41_kand.sv
 rtl/v41rom/ot_v41_chain3.sv rtl/v41rom/ot_v41_chain4.sv rtl/v41rom/ot_v41_fadd2.sv rtl/v41rom/ot_v41_rom_elem_w10.sv
 rtl/v41rom/ot_v41_bterm.sv rtl/v41rom/ot_v41_chain.sv rtl/v41rom/ot_v41_segtree.sv rtl/v41rom/ot_v41_bf16_lanes.sv
 rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_cg.sv
 rtl/proto/ot_fp32_add_rne_pipe.sv 
 rtl/v41rom/ot_v41_fadd.sv rtl/common/ot_prefix.sv rtl/v41rom/ot_v41_bterm2_w10.sv rtl/v41rom/ot_v41_chain2.sv
 rtl/v41rom/ot_v41_segtree2.sv rtl/v41rom/ot_v41_bf16_lanes2.sv rtl/v41rom/ot_v41_bterm3_w10.sv rtl/v41rom/ot_v41_bterm4_w10.sv
 rtl/v41rom/ot_v41_bterm5_w10.sv rtl/v41rom/ot_v41_segtree3.sv rtl/v41rom/ot_v41_segtree4.sv rtl/v41rom/ot_v41_segtree5.sv
 rtl/v41rom/ot_v41_segtree6.sv "
F=""; for f in $RTL; do F="$F $S/$f"; done
build() { # name defines...
  local n=$1; shift
  "$V" --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_qxpq_cpr --Mdir "$W/$n" -j 16 -CFLAGS -O1 \
    "$@" $F "$TB" > "$W/$n.build.log" 2>&1 || { echo "BUILD_FAIL $n"; tail -20 "$W/$n.build.log"; return 1; }
}
run() { # name expect seed
  "$W/$1/Vtb_qxpq_cpr" +seed=$3 > "$W/$1_s$3.log" 2>&1
  local v=$(grep -o "QXPQ_CPR \(PASS\|FAIL\)" "$W/$1_s$3.log" | tail -1)
  local ok=0; [ "$v" = "QXPQ_CPR PASS" ] && [ "$2" = pass ] && ok=1; [ "$v" = "QXPQ_CPR FAIL" ] && [ "$2" = fail ] && ok=1
  echo "$1 seed $3 expect $2 -> ${v:-NO_VERDICT} $([ $ok = 1 ] && echo OK || echo BAD)"
  grep '^QXPQ_CPR cycles' "$W/$1_s$3.log"   # own line: the closure loop's min_count_regex counts it (windows=N)
  [ $ok = 1 ]
}
MODE=${3:-all}
case "$MODE" in
  pass) build pass || exit 2; rc=0; for s in 1 2 3; do run pass pass $s || rc=1; done; echo "BENCH_RC $rc"; exit $rc ;;
  mut_go|mut_busy|mut_late)
    case $MODE in mut_go) D=+define+OT_QXPQ_CPR_MUT_GO ;; mut_busy) D=+define+OT_QXPQ_CPR_MUT_BUSY ;; *) D=+define+TB_MUT_LATE ;; esac
    build $MODE $D || exit 2
    if run $MODE fail 1; then echo "MUTANT_DETECTED $MODE"; exit 1; fi
    echo "MUTANT_ESCAPED $MODE"; exit 0 ;;
  all) ;;
  *) echo "unknown MODE $MODE"; exit 2 ;;
esac
rc=0
build pass && build mut_go +define+OT_QXPQ_CPR_MUT_GO && build mut_busy +define+OT_QXPQ_CPR_MUT_BUSY && build mut_late +define+TB_MUT_LATE || exit 2
for s in 1 2 3; do run pass pass $s || rc=1; done
run mut_go fail 1 || rc=1
run mut_busy fail 1 || rc=1
run mut_late fail 1 || rc=1
echo "BENCH_RC $rc"
exit $rc
