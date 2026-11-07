#!/bin/bash
# lock-step bench: original gqi_issue (82d223825a, before any retime) vs d360f93f86 + ex_we without fire, + mutants
set -u
O=/srv/opentallas-scratch2/claude/die-hbm-83-coll/gqi; G=/srv/opentallas-scratch2/claude/die-hbm-82-coll/gqi; W=/srv/opentallas-scratch2/claude/die-hbm-82-coll/wt-gqi; B=$O/bench; mkdir -p $B; cd $B
F=rtl/hbm_accel/cores_split/reform_1105s/gq/ot_hgi_coll_gqi_issue.sv
git -C $W show 82d223825a:$F | sed 's/^module ot_hgi_coll_gqi_issue #/module ot_hgi_coll_gqi_issue_ref #/' > ref.sv
cp $W/$F dut0.sv
python3 -I ${MKB:-$G/mkbench.py} dut0.sv tb.sv
DEPS="$W/rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv $W/rtl/lib/ot_rst_relay.sv"
sed 's/ex_we\[r\*64 +: 64\] <= (ev_v\[S_P-2\] \&\& /ex_we[r*64 +: 64] <= (/' dut0.sv > dut1.sv
sed 's/ex_we\[r\*64 +: 64\] <= (ev_v\[S_P-2\]/ex_we[r*64 +: 64] <= (ev_v[S_P-1]/' dut0.sv > dut2.sv
sed 's/ \&\& fv(ev_k\[S_P-2\], r) \&\& is_code(i))/ \&\& is_code(i))/' dut0.sv > dut3.sv
sed 's/ \&\& fv(ev_k\[S_P-2\], r) \&\& is_code(i))/ \&\& fv(ev_k[S_P-2], r))/' dut0.sv > dut4.sv
sed 's/(ev_v\[S_P-2\] \&\& g_qbg \&\& fv/(ev_v[S_P-2] \&\& fv/' dut0.sv > dut5.sv
sed 's/ex <= ex_n; ex_z <= fire;/ex <= ex_n; ex_z <= 1'"'"'b0;/' dut0.sv > dut6.sv
sed 's/wire \[2:0\] g_src_n3 = fire ? rc\[39:37\] : g_src\[2:0\];/wire [2:0] g_src_n3 = g_src[2:0];/' dut0.sv > dut7.sv
for m in 1 2 3 4 5 6 7; do cmp -s dut0.sv dut$m.sv && echo "MUTANT $m NOT APPLIED"; done
V=$HOME/.local/opentallas-tools/bin/verilator
run() { "$V" --binary --timing -O1 -j 4 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-MULTITOP -Wno-TIMESCALEMOD -Wno-lint -Wno-style \
    -DRMUT=0 -DDMUT=$3 -DSEED=$4 -DNCYC=$5 --top-module tb --Mdir obj_$1_$4 tb.sv ref.sv $2 $DEPS > $1_$4.clog 2>&1 || { echo "$1 COMPILE FAIL"; grep -m5 -i error $1_$4.clog; return; }
  obj_$1_$4/Vtb > $1_$4.log 2>&1; echo "$1 $(grep LOCKSTEP $1_$4.log) $(grep -m1 MISMATCH $1_$4.log | cut -c1-120)"; rm -rf obj_$1_$4; }
for s in 1 2 3 4 5 6 7 8; do run clean dut0.sv 0 $s 20000 & done
wait
for s in 31 32 33 34; do run clean dut0.sv 0 $s 60000 & done
run mutB2 dut0.sv 2 11 20000 &
for m in 1 2 3 4 5 6 7; do run mut$m dut$m.sv 0 2$m 20000 & done
wait
