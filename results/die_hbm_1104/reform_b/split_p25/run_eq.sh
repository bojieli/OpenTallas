#!/usr/bin/env bash
# run_eq.sh REPO OUT: part 25 bench, flat kport_q against the composition, both with kit face shell models.
# SW_HREG=1: the sw tile in its HREG=1 form (registered heads, one-hot K switch; cycle-exact, same verdicts expected).
# PASS: m0, slow K, E quadrant. Must FAIL: seam mutants MUT 1..4, root mutants RMUT 1 2.
set -u; cd "${1:?}"; OUT=$(realpath -m "${2:?}"); mkdir -p "$OUT"; rc=0
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
P=results/die_hbm_1104/reform_b/split_p25; S=rtl/hbm_accel/loader/service_native; D=rtl/hbm_accel/cores_split/reform_1105b
MAC=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
L="rtl/lib/ot_reset_sync.sv rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv $S/ot_hbm_svc_pc_ctrl_leaf.sv"
FW="python3 physical/die_plan/hbm/over_cap_split/reform_1103/facewrap.py --no-hier --clk-re clk --rst-re rst"
$FW --top ot_wbq_root --pass-param MUT --out $OUT/root.fs.sv -- $D/ot_wbq_split.sv > /dev/null || exit 3
$FW --top ot_wbq_sw ${SW_HREG:+--param HREG=$SW_HREG} --out $OUT/sw.fs.sv -- $D/ot_wbq_split.sv > /dev/null || exit 3
$FW --top ot_hbm_svc_wb_kport_q --out $OUT/ref.fs.sv -- $S/ot_hbm_svc_wb_kport_q.sv > /dev/null || exit 3
cat > $OUT/face_reg.sv <<'V'
module ot_hbm_face_reg #(parameter integer W=1)(input wire clk, input wire [W-1:0] d, output reg [W-1:0] q); always @(posedge clk) q<=d; endmodule
V
one() { local n=$1 e=$2; shift 2; local d=$OUT/obj_$n
  "$VL" --binary --timing -O1 -j ${J:-6} -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb_wbq "$@" -Mdir $d -o sim $P/tb_wbq.sv $P/ot_hbm_svc_wb_kport_q__p25fs.sv $D/ot_wbq_split.sv \
   $OUT/root.fs.sv $OUT/sw.fs.sv $OUT/ref.fs.sv $OUT/face_reg.sv $S/ot_hbm_svc_wb_kport_q.sv $S/ot_hbm_svc_wb_cutthrough_cdc.sv $MAC $L > $d.build.log 2>&1 || { echo "$n BUILD FAIL"; grep -m8 %Error $d.build.log | cut -c1-220; return 1; }
  timeout ${SIMT:-900} $d/sim > $d.run.log 2>&1; local r=$?; local g=PASS; [ $r != 0 ] && g=FAIL
  local v=BAD; [ $g = $e ] && v=OK
  echo "$n expect=$e got=$g $v | $(grep -E '^WBQ s' $d.run.log | tail -1 | cut -c1-230)"; [ $v = OK ]
}
for spec in ${RUNS:-m0:PASS: slow:PASS:-GSLOW=1 east:PASS:-GQUAD=1 s1:FAIL:-GMUT=1 s2:FAIL:-GMUT=2 s3:FAIL:-GMUT=3 s4:FAIL:-GMUT=4 r1:FAIL:-GRMUT=1 r2:FAIL:-GRMUT=2}; do
  IFS=: read n e f <<<"$spec"; one $n $e $f || rc=1
done
echo EQ_EXIT $rc; exit $rc
