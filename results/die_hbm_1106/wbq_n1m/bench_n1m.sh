#!/bin/bash
# bench_n1m.sh REPO OUT: ot_wbq_root r2c2 payload (OLD commit text) vs OT_WBQ_N1M. MUT0 must PASS; MUT1 read address bit 0 flipped,
# MUT2 w_mask_in 0, MUT3 write address bits [5:0] -> [5:1],~[0], MUT4 r_ce tied 1 must FAIL.
W=$1; O=$2; H=$W/results/die_hbm_1106/wbq_n1m; V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; mkdir -p $O
F=rtl/hbm_accel/cores_split/reform_1105b/ot_wbq_split.sv
M=$W/physical/asap7_memory_macros_v2; MO=$M/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v; MN=$M/ot_sram_1r1w_128x256_m1_r0c0_g256/ot_sram_1r1w_128x256_m1_r0c0_g256.v
L="$W/rtl/lib/ot_reset_sync.sv $W/rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv"
root() { awk '/^module ot_wbq_root/{p=1} p{print} p&&/^endmodule/{exit}'; }
git -C $W show ${OLD:-57ec5ae97c}:$F | root | sed 's/^module ot_wbq_root/module old_wbq_root/' > $O/old.sv
root < $W/$F | sed 's/^module ot_wbq_root/module new_wbq_root/' > $O/n0.sv
sed 's/\.r_addr_in({copy_bank,row\[5:0\]}),\.rd_out(mem_data\[g\]),$/.r_addr_in({copy_bank,row[5:1],~row[0]}),.rd_out(mem_data[g]),/' $O/n0.sv > $O/n1.sv
sed "s/\.w_mask_in(1'b1));/.w_mask_in(1'b0));/" $O/n0.sv > $O/n2.sv
sed '0,/\.w_addr_in({fill_bank,ordinal\[10:5\]})/s//.w_addr_in({fill_bank,ordinal[10:6],~ordinal[5]})/' $O/n0.sv > $O/n3.sv
sed '0,/\.r_ce_in(mem_read\[g\])/s//.r_ce_in(1'"'"'b1)/' $O/n0.sv > $O/n4.sv
for m in 0 1 2 3 4; do [ $m != 0 ] && cmp -s $O/n0.sv $O/n$m.sv && echo "m$m NOT APPLIED"; ( d=$O/m$m; rm -rf $d; $V --binary -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style -DCYC=${CYC:-40000} -DRST=${RST:-400} -DOT_WBQ_N1M --top-module tb -Mdir $d -o sim $H/tb_n1m.sv $O/old.sv $O/n$m.sv $L $MO $MN > $d.b.log 2>&1 || { echo "m$m BUILD FAIL"; tail -5 $d.b.log; exit; }; timeout 1800 $d/sim ${SEED:+"+verilator+seed+$SEED"} > $d.r.log 2>&1; echo "m$m rc=$? $(grep -E 'LOCKSTEP|MISMATCH' $d.r.log | tail -1 | tr '\n' ' ')" ) & done; wait
