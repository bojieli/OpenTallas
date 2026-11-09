#!/bin/bash
# QC-TYPES-10/HC3: lock-step of the bound form ot_qfd_xs_leaf_fo32_w #(NCH4,FILL_PIPE1,READ_PIN_PIPE1) vs the hc3 leaf
# ot_qfd_xs_leaf #(NCH4,READ_PIN_PIPE1,FILL_PIPE1,BANK_PIPE0) (tb_qfd_xs_leaf_fo32 with the dut line swapped), 3 seeds x
# 20000 ops + mutant MUT=2 (must FAIL); yosys: wrapper elaborates at the bound params, refuses FILL_PIPE 0 (must FAIL)
set -u
H=/srv/opentallas-scratch2/claude/qct10/hc3; N=$H/src_hc3; O=$H/bench_w; D=rtl/qwen_sys/dvm_20261014
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; Y=$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys
[ -x $Y ] || Y=$(ls $HOME/.local/opentallas-tools/yosys-0.68/*/yosys 2>/dev/null | head -1)
rm -rf $O; mkdir -p $O; cd $N
sed 's/ot_qfd_xs_leaf_fo32 #(.GRP(GRP),.NG(NG),.NQ(NQ),.MUT(MUT)) dut/ot_qfd_xs_leaf_fo32_w #(.NCH(4),.FILL_PIPE(1),.READ_PIN_PIPE(1),.MUT(MUT)) dut/' $D/tb_qfd_xs_leaf_fo32.sv > $O/tb_w.sv
grep -c "ot_qfd_xs_leaf_fo32_w #" $O/tb_w.sv
for cfg in "s7:-GSEED=7 -GNOPS=20000" "s11:-GSEED=11 -GNOPS=20000" "s23:-GSEED=23 -GNOPS=20000" "mut2:-GMUT=2 -GSEED=7"; do
  n=${cfg%%:*}; a=${cfg#*:}; mkdir -p $O/$n
  $V --binary --timing -j 4 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTH --x-assign 0 --x-initial 0 \
     --top-module tb_qfd_xs_leaf_fo32 --Mdir $O/$n/obj $a $O/tb_w.sv $D/ot_qfd_xs_leaf_fo32_w.sv $D/ot_qfd_xs_leaf_fo32.sv \
     $D/ot_qfd_xslice.sv rtl/hdc/ot_hdc_delay.sv -o tb > $O/$n/build.log 2>&1 || { echo "BUILD_FAIL $n"; grep -m5 %Error $O/$n/build.log; continue; }
  $O/$n/obj/tb > $O/$n/run.log 2>&1; rc=$?; grep -E "^(PASS|FAIL|MISMATCH)" $O/$n/run.log | head -3; echo "RC $n $rc"
done
echo "yosys $Y"
$Y -q -p "read_verilog -sv $D/ot_qfd_xs_leaf_fo32.sv $D/ot_qfd_xs_leaf_fo32_w.sv; chparam -set NCH 4 -set FILL_PIPE 1 -set READ_PIN_PIPE 1 ot_qfd_xs_leaf_fo32_w; hierarchy -check -top ot_qfd_xs_leaf_fo32_w; stat" > $O/yosys_ok.log 2>&1; echo "RC yosys_bound_params $?"
$Y -q -p "read_verilog -sv $D/ot_qfd_xs_leaf_fo32.sv $D/ot_qfd_xs_leaf_fo32_w.sv; chparam -set FILL_PIPE 0 ot_qfd_xs_leaf_fo32_w; hierarchy -check -top ot_qfd_xs_leaf_fo32_w" > $O/yosys_bad.log 2>&1; echo "RC yosys_fill0_must_fail $?"; grep -m2 -i "error" $O/yosys_bad.log
md5sum $D/ot_qfd_xs_leaf_fo32_w.sv $D/ot_qfd_xs_leaf_fo32.sv $D/ot_qfd_xslice.sv
