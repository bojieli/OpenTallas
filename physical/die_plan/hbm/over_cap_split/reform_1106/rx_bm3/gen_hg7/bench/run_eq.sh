#!/usr/bin/env bash
# run_eq.sh REPO OUT [NCYC]: part 20 composition == gold + declared shift, one clock (kit form) and plesiochronous; SMUT 1..9 must FAIL.
set -u; cd "${1:?}"; OUT=${2:?}; NCYC=${3:-9000}; mkdir -p "$OUT"; rc=0
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
L=rtl/dsrom_sys/s81_link; P=results/die_hbm_1104/reform_b/split_p20; R=rtl/hbm_accel/cores_split/reform_1104b/ot_pdie_serdes_split.sv
LIB="$L/ot_pdie_serdes.sv $L/ot_s81_kp4_common.sv $L/ot_s81_kp4_enc.sv rtl/hbm_accel/cores_split/reform_1104b/ot_s81_kp4_enc_la.sv $L/ot_s81_kp4_dec.sv $L/ot_s81_kp4_bm.sv $L/ot_s81_kp4_dchn.sv $L/ot_s81_kp4_ddly.sv $L/ot_s81_kp4_dout.sv $L/ot_s81_kp4_dsyn.sv"
MAC="physical/asap7_memory_macros/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v"
FW="python3 physical/die_plan/hbm/over_cap_split/reform_1103/facewrap.py"; CK='^(clk|ck)(_|$|\b)|^pma_rck$|^rck_clk$'
$FW --no-hier --top ot_pdie_serdes --clk-re "$CK" --out $OUT/ot_pdie_serdes.fs.sv -- $L/ot_pdie_serdes.sv > /dev/null || exit 3
$FW --no-hier --top ot_pdie_serdes_tx --clk-re "$CK" --out $OUT/ot_pdie_serdes_tx.fs.sv -- $R > /dev/null || exit 3
$FW --no-hier --top ot_pdie_serdes_rx --clk-re "$CK" --pass-param SEAM --out $OUT/ot_pdie_serdes_rx.fs.sv -- $R > /dev/null || exit 3
cat > $OUT/face_reg.sv <<'V'
module ot_hbm_face_reg #(parameter integer W=1)(input wire clk, input wire [W-1:0] d, output reg [W-1:0] q); always @(posedge clk) q<=d; endmodule
V
# fsp shells: recovered-domain pins on the recovered clock (bench model for MODE 1 / 2 only; the kit shell has one clock)
sed -E '/u_bin_pma_rx|u_bout_k_|u_bin_cw_q|u_bin_apply|u_bin_o_unc|u_bin_o_ne|u_bin_fs/s/\.clk\(clk\)/.clk(rck_clk)/' $OUT/ot_pdie_serdes_rx.fs.sv > $OUT/ot_pdie_serdes_rx.fsp.sv
sed -E '/u_bin_pma_rx/s/\.clk\(clk\)/.clk(pma_rck)/' $OUT/ot_pdie_serdes.fs.sv > $OUT/ot_pdie_serdes.fsp.sv
one() { # m ft mode expect
  local d=$OUT/m$1_f$2_c$3 x=fs; [ $3 != 0 ] && x=fsp
  local SRC="$LIB $R $MAC $OUT/ot_pdie_serdes.$x.sv $OUT/ot_pdie_serdes_tx.fs.sv $OUT/ot_pdie_serdes_rx.$x.sv $OUT/face_reg.sv $P/ot_pdie_serdes__p20fs.sv $P/tb_pdie_p20.sv"
  "$VL" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-lint -Wno-style -I$L -Irtl/hbm_accel/cores_split/reform_1104b --top-module tb_pdie_p20 \
    -GSMUT=$1 -GFT=$2 -GMODE=$3 -GNCYC=$NCYC -Mdir $d $SRC --build-jobs ${J:-4} > $d.build.log 2>&1 || { echo "m$1 f$2 c$3 BUILD FAIL"; grep -m6 %Error $d.build.log; return 1; }
  $d/Vtb_pdie_p20 > $d.run.log 2>&1
  local r=$(grep -oE '^P20_EQ (PASS|FAIL)' $d.run.log | awk '{print $2}'); local v=BAD; [ "$r" = "$4" ] && v=OK
  echo "smut$1 ft$2 mode$3 expect=$4 got=${r:-NONE} $v | $(grep -E '^P20_' $d.run.log | tr '\n' ' ' | cut -c1-300)"; [ $v = OK ]
}
for spec in ${RUNS:-0:1:0:PASS 0:2:0:PASS 0:1:1:PASS 0:1:2:PASS 1:1:0:FAIL 2:2:0:FAIL 3:1:0:FAIL 4:1:0:FAIL 5:1:0:FAIL 6:1:0:FAIL 7:1:0:FAIL 8:1:0:FAIL 9:1:0:FAIL 1:1:1:FAIL}; do
  IFS=: read m f c e <<<"$spec"; one $m $f $c $e || rc=1
done
echo EQ_EXIT $rc; exit $rc
