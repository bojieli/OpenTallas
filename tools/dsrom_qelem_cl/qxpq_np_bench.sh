#!/bin/bash
# S81-QXPQ3 bench runner: tb_qxpq_np (NP=1 vs NP=0, both RSTP=1 CPR=1, routed params): pass x3 seeds or one mutant
# (copy of qxpq_cpr_bench.sh).  Extra RTL files: NP_EXTRA (space separated, relative to SRC_ROOT).
#   qxpq_cpr_bench.sh SRC_ROOT WORK [MODE]   (SRC_ROOT = source tree with rtl/ and tools/; ROMs = the tb fixtures)
#   MODE pass (default): positive run x3 seeds (BENCH_RC 0 on PASS);
#   mut:<DEFINE>: one mutant built with +define+<DEFINE>, prints MUTANT_DETECTED and exits 1 when the bench FAILs it
#   (closure-loop expect=fail); mut:TB_MUT_LATE is the bench self-check (dut go one cycle early).
set -u
S=$(cd "$1" && pwd); W=$2; mkdir -p "$W"; W=$(cd "$W" && pwd)
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
TB=$S/tools/dsrom_qelem_cl/tb_qxpq_np.sv
RTL="rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10.sv rtl/v41rom/ot_v41_rom_elem_qx_pq_w10.sv rtl/v41rom/ot_v41_elem_pq_tags.sv rtl/v41rom/ot_v41_kreg.sv
 rtl/v41rom/ot_v41_chain3.sv rtl/v41rom/ot_v41_chain4.sv rtl/v41rom/ot_v41_fadd2.sv rtl/v41rom/ot_v41_rom_elem_w10.sv
 rtl/v41rom/ot_v41_bterm.sv rtl/v41rom/ot_v41_chain.sv rtl/v41rom/ot_v41_segtree.sv rtl/v41rom/ot_v41_bf16_lanes.sv
 rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_cg.sv
 rtl/proto/ot_fp32_add_rne_pipe.sv 
 rtl/v41rom/ot_v41_fadd.sv rtl/common/ot_prefix.sv rtl/v41rom/ot_v41_bterm2_w10.sv rtl/v41rom/ot_v41_chain2.sv
 rtl/v41rom/ot_v41_segtree2.sv rtl/v41rom/ot_v41_bf16_lanes2.sv rtl/v41rom/ot_v41_bterm3_w10.sv rtl/v41rom/ot_v41_bterm4_w10.sv
 rtl/v41rom/ot_v41_bterm5_w10.sv rtl/v41rom/ot_v41_segtree3.sv rtl/v41rom/ot_v41_segtree4.sv rtl/v41rom/ot_v41_segtree5.sv
 rtl/v41rom/ot_v41_segtree6.sv rtl/v41rom/ot_v41_fadd_np.sv rtl/v41rom/ot_v41_segtree7.sv rtl/v41rom/ot_v41_chain5.sv
 physical/asap7_memory_macros/ot_sram_1r1w_128x64_m1_p192/ot_sram_1r1w_128x64_m1_p192.v ${NP_EXTRA:-}"
F=""; for f in $RTL; do F="$F $S/$f"; done
build() { # name defines...
  local n=$1; shift
  "$V" --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_qxpq_np --Mdir "$W/$n" -j 16 -CFLAGS -O1 \
    "$@" $F "$TB" > "$W/$n.build.log" 2>&1 || { echo "BUILD_FAIL $n"; tail -20 "$W/$n.build.log"; return 1; }
}
run() { # name expect seed
  "$W/$1/Vtb_qxpq_np" +seed=$3 > "$W/$1_s$3.log" 2>&1
  local v=$(grep -o "QXPQ_NP \(PASS\|FAIL\)" "$W/$1_s$3.log" | tail -1)
  local ok=0; [ "$v" = "QXPQ_NP PASS" ] && [ "$2" = pass ] && ok=1; [ "$v" = "QXPQ_NP FAIL" ] && [ "$2" = fail ] && ok=1
  echo "$1 seed $3 expect $2 -> ${v:-NO_VERDICT} $([ $ok = 1 ] && echo OK || echo BAD)"
  grep '^QXPQ_NP cycles' "$W/$1_s$3.log"   # own line: the closure loop's min_count_regex counts it (windows=N)
  [ $ok = 1 ]
}
MODE=${3:-pass}
case "$MODE" in
  pass) build pass || exit 2; rc=0; for s in 1 2 3; do run pass pass $s || rc=1; done; echo "BENCH_RC $rc"; exit $rc ;;
  chk:*)
    M=${MODE#chk:}; build chk +define+$M || exit 2; rc=0; for s in 1 2 3; do run chk pass $s || rc=1; done; echo "BENCH_RC $rc"; exit $rc ;;
  mut:*)
    M=${MODE#mut:}; build $M +define+$M || exit 2
    if run $M fail 1; then echo "MUTANT_DETECTED $M"; exit 1; fi
    echo "MUTANT_ESCAPED $M"; exit 0 ;;
  *) echo "unknown MODE $MODE (pass | mut:<DEFINE>)"; exit 2 ;;
esac
