#!/usr/bin/env bash
# run_eq.sh REPO OUT: part 21 bench (full-shape exact, tb_selector_s3 checks) on composition + kit face shell model.
# PASS: m0 RT6 SKEW4. Must FAIL: DMUT 1 3 5 6, RT5 (choose margin), DRAIN3, MUT 1..4 (seam).
set -u; cd "${1:?}"; OUT=$(realpath -m "${2:?}"); mkdir -p "$OUT/vec"; rc=0
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
P=results/die_hbm_1104/reform_b/split_p21; S=rtl/hbm_accel/index/sel_s3
MAC=physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
FW="python3 physical/die_plan/hbm/over_cap_split/reform_1103/facewrap.py"
python3 -I $P/vec.py "$OUT/vec" || exit 3
$FW --no-hier --top ot_hidx_s3_ctl --pass-param DMUT --out $OUT/ctl.fs.sv -- $S/ot_hidx_s3_ctl.sv rtl/lib/ot_rst_relay.sv > /dev/null || exit 3
$FW --no-hier --top ot_hidx_s3_q --pass-param DMUT --out $OUT/q.fs.sv -- $S/ot_hidx_s3_q.sv rtl/lib/ot_rst_relay.sv > /dev/null || exit 3
cat > $OUT/face_reg.sv <<'V'
module ot_hbm_face_reg #(parameter integer W=1)(input wire clk, input wire [W-1:0] d, output reg [W-1:0] q); always @(posedge clk) q<=d; endmodule
V
one() { # name expect gflags...
  local n=$1 e=$2; shift 2; local d=$OUT/obj_$n
  "$VL" --binary --timing -O1 -j ${J:-4} -Wno-fatal -Wno-lint -Wno-style --top-module tb_selector_s3 "$@" -Mdir $d \
    $S/ot_hidx_s3_ctl.sv $S/ot_hidx_s3_q.sv rtl/lib/ot_rst_relay.sv $MAC $OUT/ctl.fs.sv $OUT/q.fs.sv $OUT/face_reg.sv $P/ot_hbm_idx_selector_static_sel__p21fs.sv $P/tb_selector_p21.sv > $d.build.log 2>&1 \
    || { echo "$n BUILD FAIL"; grep -m6 %Error $d.build.log | cut -c1-200; return 1; }
  (cd $OUT/vec && $d/Vtb_selector_s3) > $d.run.log 2>&1; local r=$?; local g=PASS; [ $r != 0 ] && g=FAIL
  local v=BAD; [ $g = $e ] && v=OK
  echo "$n expect=$e got=$g $v | $(grep -E '^IDX_SELECTOR_S3' $d.run.log | tail -1 | cut -c1-130)"; [ $v = OK ]
}
for spec in ${RUNS:-m0:PASS: d1:FAIL:-GDMUT=1 d3:FAIL:-GDMUT=3 d5:FAIL:-GDMUT=5 d6:FAIL:-GDMUT=6 rt5:FAIL:-GRT=5 dr3:FAIL:-GDRAIN=3 s1:FAIL:-GMUT=1 s2:FAIL:-GMUT=2 s3:FAIL:-GMUT=3 s4:FAIL:-GMUT=4}; do
  IFS=: read n e f <<<"$spec"; one $n $e $f || rc=1
done
echo EQ_EXIT $rc; exit $rc
