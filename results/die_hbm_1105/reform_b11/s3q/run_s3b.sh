#!/bin/bash
# run_s3b.sh WT OUT: lock-step old (git rev OLD, B7 tie form) vs new s3_q S2B form; MUT 0 PASS, DMUT 1 6..13 FAIL
# mode A (default): legal schedule, op1 >= G1=8 after op6/op7, qfault compared and must stay 0. mode B: QCMP=0 G1=3 TAG=b, op1 right behind the scan, qfault not compared.
W=$1; O=$2; OLD=${OLD:-c299a5dfc1}; H=$(cd "$(dirname "$0")"; pwd); V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; mkdir -p $O
S=rtl/hbm_accel/index/sel_s3/ot_hidx_s3_q.sv
git -C $W show $OLD:$S | sed -E 's/\bot_hidx_s3_(q|pfx|pri)\b/old_hidx_s3_\1/g' > $O/old.sv
M=$W/physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
one(){ d=$O/o$1${TAG:-}; rm -rf $d; $V --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style -DCYC=${CYC:-30000} -DGAP=${GAP:-8} -DG1=${G1:-8} -DQCMP=${QCMP:-1} -GDMUT=$1 --top-module tb -Mdir $d -o sim $H/tb_s3b.sv $O/old.sv $W/$S $W/rtl/lib/ot_rst_relay.sv $M > $d.b.log 2>&1 || { echo "m$1 BUILD FAIL"; tail -3 $d.b.log; return; }; timeout 1800 $d/sim > $d.r.log 2>&1; echo "m$1 rc=$? $(grep -E '^S3Q|^QFAULT|^PASS|FAIL' $d.r.log | tr '\n' ' ') $(grep -m1 DIFF $d.r.log)"; }
for m in ${MUTS:-0 1 6 7 8 9 10 11 12 13}; do one $m & done; wait
echo ALLDONE
