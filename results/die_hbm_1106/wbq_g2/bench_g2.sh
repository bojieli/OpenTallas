#!/bin/bash
# bench_g2.sh REPO OUT: ot_wbq_root (OT_WBQ_N1M) vs the lane-group split ot_wbq_root_g2 (two ot_wbq_root_grp), lock-step, every
# output every hbm_clk / fifo_clk edge (tb_n1m.sv). m0 must PASS; mutants must FAIL:
#  m1 the g1 master built as G=0 (wrong lane ids), m2 wd4/wd5 swapped at the composition, m3 group pick priority lane 1 before lane 0,
#  m4 g_credit bits swapped.
W=$1; O=$2; H=$W/results/die_hbm_1106/wbq_g2; T=$W/results/die_hbm_1106/wbq_n1m/tb_n1m.sv
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; mkdir -p $O
F=$W/rtl/hbm_accel/cores_split/reform_1105b/ot_wbq_split.sv
MN=$W/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r0c0_g256/ot_sram_1r1w_128x256_m1_r0c0_g256.v
L="$W/rtl/lib/ot_reset_sync.sv $W/rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv"
mod() { awk -v m="$1" '$0 ~ "^module "m"( |#|\\()"{p=1} p{print} p&&/^endmodule/{exit}' $F; }
mod ot_wbq_root | sed 's/^module ot_wbq_root/module old_wbq_root/' > $O/old.sv
{ mod ot_wbq_root_grp; mod ot_wbq_root_g0; mod ot_wbq_root_g1; mod ot_wbq_root_g2 | sed 's/^module ot_wbq_root_g2/module new_wbq_root/'; } > $O/n0.sv
sed 's/ot_wbq_root_grp #(.G(1),.CRED(CRED),.MUT(MUT)) u_grp/ot_wbq_root_grp #(.G(0),.CRED(CRED),.MUT(MUT)) u_grp/' $O/n0.sv > $O/n1.sv
sed 's/\.wd0(wd4),\.wd1(wd5)/.wd0(wd5),.wd1(wd4)/' $O/n0.sv > $O/n2.sv
sed "s/wire \[1:0\] sel=ne\[0\]?2'd0:ne\[1\]?2'd1:/wire [1:0] sel=ne[1]?2'd1:ne[0]?2'd0:/" $O/n0.sv > $O/n3.sv
sed 's/\.g_credit(g_credit\[0\])/.g_credit(g_credit[1])/; s/\.g_credit(g_credit\[1\]),\n/X/' $O/n0.sv | awk '/u_g1/{f=1} f&&/g_credit\(g_credit\[1\]\)/{sub(/g_credit\[1\]/,"g_credit[0]");f=0} {print}' > $O/n4.sv
for m in 0 1 2 3 4; do [ $m != 0 ] && cmp -s $O/n0.sv $O/n$m.sv && echo "m$m NOT APPLIED"; ( d=$O/m$m; rm -rf $d; $V --binary -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style -DCYC=${CYC:-40000} -DRST=${RST:-400} -DOT_WBQ_N1M --top-module tb -Mdir $d -o sim $T $O/old.sv $O/n$m.sv $L $MN > $d.b.log 2>&1 || { echo "m$m BUILD FAIL"; grep -m5 %Error $d.b.log; exit; }; timeout 1800 $d/sim ${SEED:+"+verilator+seed+$SEED"} > $d.r.log 2>&1; echo "m$m rc=$? $(grep -E 'LOCKSTEP|MISMATCH' $d.r.log | tail -1 | tr '\n' ' ')" ) & done; wait
