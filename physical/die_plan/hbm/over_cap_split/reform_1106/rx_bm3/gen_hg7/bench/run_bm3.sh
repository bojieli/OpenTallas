#!/usr/bin/env bash
# run_bm3.sh OUT [NCYC]: BM3 face-shelled form (ot_pdie_serdes__bm3fs.sv) == gold ot_pdie_serdes__fs + declared shift, MODE 0 (kit, one clock).
set -u; B=$(cd "$(dirname "$0")" && pwd); cd "$B/repo"; OUT=${1:?}; NCYC=${2:-9000}; mkdir -p "$OUT"; rc=0
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
L=rtl/dsrom_sys/s81_link; R=rtl/hbm_accel/cores_split/reform_1104b/ot_pdie_serdes_split.sv
LIB="$L/ot_pdie_serdes.sv $L/ot_s81_kp4_common.sv $L/ot_s81_kp4_enc.sv rtl/hbm_accel/cores_split/reform_1104b/ot_s81_kp4_enc_la.sv $L/ot_s81_kp4_dec.sv $L/ot_s81_kp4_bm.sv $L/ot_s81_kp4_dchn.sv $L/ot_s81_kp4_ddly.sv $L/ot_s81_kp4_dout.sv $L/ot_s81_kp4_dsyn.sv"
MAC="physical/asap7_memory_macros/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v"
FW="python3 physical/die_plan/hbm/over_cap_split/reform_1103/facewrap.py"; CK="^(clk|ck)(_|\$|\\b)|^pma_rck\$|^rck_clk\$"
[ -f $OUT/ot_pdie_serdes.fs.sv ] || $FW --no-hier --top ot_pdie_serdes --clk-re "$CK" --out $OUT/ot_pdie_serdes.fs.sv -- $L/ot_pdie_serdes.sv > $OUT/fw1.log 2>&1 || exit 3
[ -f $OUT/ot_pdie_serdes_tx.fs.sv ] || $FW --no-hier --top ot_pdie_serdes_tx --clk-re "$CK" --out $OUT/ot_pdie_serdes_tx.fs.sv -- $R > $OUT/fw2.log 2>&1 || exit 3
cat > $OUT/face_reg.sv <<V
module ot_hbm_face_reg #(parameter integer W=1)(input wire clk, input wire [W-1:0] d, output reg [W-1:0] q); always @(posedge clk) q<=d; endmodule
V
one() { # seam bmut smut ft rxd fd expect
  local d=$OUT/s$1_b$2_m$3_f$4_r$5_d$6
  local SRC="$LIB $R ot_pdie_serdes_rx_bm3.sv $MAC $OUT/ot_pdie_serdes.fs.sv $OUT/ot_pdie_serdes_tx.fs.sv $OUT/face_reg.sv $B/ot_pdie_serdes__bm3fs.sv $B/tb_bm3.sv"
  "$VL" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-lint -Wno-style -I$L -Irtl/hbm_accel/cores_split/reform_1104b --top-module tb_bm3 \
    -GSEAM=$1 -GBMUT=$2 -GSMUT=$3 -GFT=$4 -GRXD=$5 -GFD=$6 -GMODE=0 -GNCYC=$NCYC -Mdir $d $SRC --build-jobs ${J:-4} > $d.build.log 2>&1 || { echo "s$1 b$2 m$3 f$4 BUILD FAIL"; grep -m6 %Error $d.build.log; return 1; }
  $d/Vtb_bm3 > $d.run.log 2>&1
  local r=$(grep -oE "^P20_EQ (PASS|FAIL)" $d.run.log | awk "{print \$2}"); local v=BAD; [ "$r" = "$7" ] && v=OK
  echo "seam$1 bmut$2 smut$3 ft$4 rxd$5 fd$6 expect=$7 got=${r:-NONE} $v | $(grep -E "^P20_" $d.run.log | tr "\n" " " | cut -c1-400)"; [ $v = OK ]
}
for spec in ${RUNS:?}; do IFS=: read s b m f x y e <<<"$spec"; one $s $b $m $f $x $y $e || rc=1; done
echo EQ_EXIT $rc; exit $rc
