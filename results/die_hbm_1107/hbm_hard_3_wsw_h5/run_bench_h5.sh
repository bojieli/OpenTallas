#!/bin/bash
# run_bench.sh BENCHDIR REPO : k3 suite (flat vs HREG=4) + lock-step suite (HREG=3 vs HREG=4), mutants must fail
B=$1; R=$2; cd $R || exit 9
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
B0=/srv/opentallas-scratch3/claude/hbm-hard-1/bench/k3c
SRC="/srv/opentallas-scratch3/claude/hbm-hard-3/wsw_h5bench/split_sel16.sv $B0/root.fs.sv $B0/sw.fs.sv $B/sw1.sv $B0/face_reg.sv $B/p25fs1.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v rtl/lib/ot_reset_sync.sv rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv rtl/hbm_accel/loader/service_native/ot_hbm_svc_pc_ctrl_leaf.sv"
one(){ # tag top expect args...
 t=$1; top=$2; ex=$3; shift 3
 O=$B/o_$t; rm -rf $O
 if [ $top = tb_k3 ]; then X="$B/tb_k3.sv results/die_hbm_1104/reform_b/split_p25/ot_hbm_svc_wb_kport_q__p25fs.sv"; else X="$B/tb_h4.sv"; fi
 $V --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module $top "$@" -Mdir $O -o sim $X $SRC > $O.build.log 2>&1
 $O/sim > $O.run.log 2>&1; rc=$?
 g=PASS; [ $rc != 0 ] && g=FAIL; grep -qE "(WBQ|LOCK) PASS" $O.run.log || g=FAIL
 cm=$(grep -c "HREG2_COPY_MISMATCH" $O.run.log)
 ok=OK; [ $g != $ex ] && ok=WRONG; [ $ex = PASS ] && [ "$cm" != 0 ] && ok=WRONG
 echo "$t expect=$ex got=$g $ok copymis=$cm | $(grep -E '^(WBQ sectors|LOCK diff)' $O.run.log | head -2 | tr '\n' ' ')"
 rm -rf $O
}
for spec in "m0:" "slow:-GSLOW=1" "east:-GQUAD=1"; do t=${spec%%:*}; a=${spec#*:}; one k_$t tb_k3 PASS $a & done; wait
for spec in "k1:-GKMUT=1" "k2:-GKMUT=2" "k3:-GKMUT=3" "k4:-GKMUT=4" "r2:-GRMUT=2"; do t=${spec%%:*}; a=${spec#*:}; one k_$t tb_k3 FAIL $a & done; wait
for spec in "m0:" "slow:-GSLOW=1" "east:-GQUAD=1"; do t=${spec%%:*}; a=${spec#*:}; one l_$t tb_h4 PASS $a & done; wait
for spec in "k5:-GKMUT=5" "k6:-GKMUT=6" "k7:-GKMUT=7" "k8:-GKMUT=8" "k1:-GKMUT=1"  "k2:-GKMUT=2"; do t=${spec%%:*}; a=${spec#*:}; one l_$t tb_h4 FAIL $a & done; wait
for spec in "k9:-GKMUT=9"; do t=${spec%%:*}; a=${spec#*:}; one k_$t tb_k3 FAIL $a & one l_$t tb_h4 FAIL $a & done; wait
