#!/bin/bash
# qxpq_split_bench.sh SRC_ROOT OUT [pass|all]  (DIE-S81-65 2026-11-05, S81 rom_q 2-way split)
# tb_qxpq_split: ot_v41_rom_elem_q_qxpq_w10_gb_split (2 x NB = 1, MSEL 0 / 1) vs the NB = 2 _gb element, all-output
# lock-step at the rom_q kit parameters.  pass = three seeds; all = pass + mutants (each must FAIL):
#   mut_msel (the second half built MSEL 0), mut_wrap (ref NB = 2 tag table with the old wrapped index).
set -u
S=$(cd "$1" && pwd); W=$2; mkdir -p "$W"; W=$(cd "$W" && pwd)
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
TB=$S/tools/dsrom_qelem_cl/tb_qxpq_split.sv
echo "verilator $("$V" --version)"
RTL="rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10_gb_split.sv rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10_gb.sv rtl/v41rom/ot_v41_rom_elem_qx_pq_w10.sv rtl/v41rom/ot_v41_elem_pq_tags.sv rtl/v41rom/ot_v41_kreg.sv
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
  "$V" --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_qxpq_split --Mdir "$W/$n" -j 16 -CFLAGS -O1 \
    "$@" $F "$TB" > "$W/$n.build.log" 2>&1 || { echo "BUILD_FAIL $n"; tail -20 "$W/$n.build.log"; return 1; }
}
run() { # name expect seed
  "$W/$1/Vtb_qxpq_split" +seed=$3 > "$W/$1_s$3.log" 2>&1
  local v=$(grep -o "QXPQ_SPLIT \(PASS\|FAIL\)" "$W/$1_s$3.log" | tail -1)
  local ok=0; [ "$v" = "QXPQ_SPLIT PASS" ] && [ "$2" = pass ] && ok=1; [ "$v" = "QXPQ_SPLIT FAIL" ] && [ "$2" = fail ] && ok=1
  echo "$1 seed $3 expect $2 -> ${v:-NO_VERDICT} $([ $ok = 1 ] && echo OK || echo BAD)"
  grep '^QXPQ_SPLIT cycles' "$W/$1_s$3.log"
  [ $ok = 1 ]
}
MODE=${3:-all}
build pass || exit 2
rc=0; for s in 1 2 3; do run pass pass $s || rc=1; done
if [ "$MODE" = all ]; then
  build mut_msel +define+OT_QXPQ_SPLIT_MUT_MSEL && build mut_wrap +define+OT_PQT_MUT_WRAP || exit 2
  run mut_msel fail 1 || rc=1
  run mut_wrap fail 1 || rc=1
fi
echo "BENCH_RC $rc"
exit $rc
