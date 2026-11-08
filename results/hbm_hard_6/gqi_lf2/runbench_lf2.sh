#!/bin/bash
# runbench_f.sh REPO BENCHDIR
set -u
R=$1; B=$2; mkdir -p $B; cd $B
F=rtl/hbm_accel/cores_split/reform_1105s/gq/ot_hgi_coll_gqi_issue.sv
git -C $R show 82d223825a:$F | sed 's/^module ot_hgi_coll_gqi_issue #/module ot_hgi_coll_gqi_issue_ref #/' > ref.sv
cp /srv/opentallas-scratch3/claude/hbm-hard-5/gqi_lf_bench/dut_lf2.sv dut0.sv
python3 -I /srv/opentallas-scratch3/claude/hbm-hard-1-gq/tools/mkbench_f.py dut0.sv tb.sv
DEPS="$R/rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv $R/rtl/lib/ot_rst_relay.sv"
sed 's/ld_fire <= fire;/ld_fire <= fire_c;/' dut0.sv > dut1.sv
sed "s/row_miss <= 1'b1;/row_miss <= 1'b0;/" dut0.sv > dut2.sv
sed "s/else begin lps <= lps - 16'd1; tl <= 16'd0; cur <= b0; cur_t <= b0; end/else begin lps <= lps - 16'd1; tl <= 16'd0; cur <= b0; end/" dut0.sv > dut3.sv
sed "s/if (fire_c) begin cur <= cur + 4'd1; cur_t <= cur_t + 4'd1; end/if (fire_c) begin cur <= cur + 4'd1; end/" dut0.sv > dut4.sv
sed 's/assign aq_sel_l\[L\*64 +: 64\] = aq_sel_k;/assign aq_sel_l[L*64 +: 64] = (L==3) ? {aq_sel_k[62:0],aq_sel_k[63]} : aq_sel_k;/' dut0.sv > dut5.sv
sed 's/assign pd_m_l\[L\*4 +: 4\] = pd_m_k;/assign pd_m_l[L*4 +: 4] = (L==5) ? ~pd_m_k : pd_m_k;/' dut0.sv > dut6.sv
sed 's/ex_v\[r\] <= ev_v\[S_P-3\] \&\&/ex_v[r] <= ev_v[S_P-2] \&\&/' dut0.sv > dut7.sv
sed 's/ \&\& fv_n(ev_k\[S_P-3\], r, g_r2_n, g_f_n) \&\& code_n(j, g_qbg_n, g_bs_n);/ \&\& code_n(j, g_qbg_n, g_bs_n);/' dut0.sv > dut8.sv
sed 's/ \&\& fv_n(ev_k\[S_P-3\], r, g_r2_n, g_f_n) \&\& code_n(j, g_qbg_n, g_bs_n);/ \&\& fv_n(ev_k[S_P-3], r, g_r2_n, g_f_n);/' dut0.sv > dut9.sv
sed "s/ex <= ex_n; ex_z <= fire;/ex <= ex_n; ex_z <= 1'b0;/" dut0.sv > dut10.sv
sed 's/active <= run_q || busy || p_sv_q;/active <= run_q || busy;/' dut0.sv > dut11.sv
sed 's/always @(posedge clk) rc <= rf\[cur\];/always @(posedge clk) rc <= rf[b0];/' dut0.sv > dut12.sv
sed 's/wire \[2:0\] src_l = fire_k ? rc\[39:37\] : g_src\[2:0\];/wire [2:0] src_l = g_src[2:0];/' dut0.sv > dut13.sv
sed 's/else fire_k <= fire_c;/else fire_k <= (L==2) ? fire : fire_c;/' dut0.sv > dut15.sv
sed 's/if (p_sv_q \&\& (run_q || busy || ps_bad)) fault <= 1.b1;/if (p_sv \&\& (run || busy || ps_bad)) fault <= 1'"'"'b1;/' dut0.sv > dut14.sv
sed "s/wire \[9:0\]  ik_n     = fire ? 10'd0 : (ev_in_v ? ik + 10'd1 : ik);/wire [9:0]  ik_n     = fire ? 10'd0 : (ik + 10'd1);/" dut0.sv > dut16.sv
sed 's/pa_v\[r\] <= fv_n(ev_k\[S_PR-2\], r, g_r2_n, g_f_n);/pa_v[r] <= fv_n(ev_k[S_PR-1], r, g_r2_n, g_f_n);/' dut0.sv > dut17.sv
sed "s/qa_s\[(r\*4+w)\*13 +: 13\] <= g_srcl_n + 13'({i, 2'b00} + w);/qa_s[(r*4+w)*13 +: 13] <= g_srcl_n + 13'({i, 2'b00});/" dut0.sv > dut18.sv
sed "s/wire \[12:0\] g_srcl_n = fire ? rc\[49:37\] : g_src\[12:0\];/wire [12:0] g_srcl_n = g_src[12:0];/" dut0.sv > dut19.sv
for m in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19; do cmp -s dut0.sv dut$m.sv && echo "MUTANT $m NOT APPLIED"; done
V=$HOME/.local/opentallas-tools/bin/verilator
run() { "$V" --binary --timing -O1 -j 2 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-MULTITOP -Wno-TIMESCALEMOD -Wno-lint -Wno-style \
    -DRMUT=0 -DDMUT=$3 -DSEED=$4 -DNCYC=$5 -DRQ=6 ${GD:-} --top-module tb --Mdir obj_$1_$4 tb.sv ref.sv $2 $DEPS > $1_$4.clog 2>&1 || { echo "$1 COMPILE FAIL"; grep -m5 -i error $1_$4.clog; return; }
  obj_$1_$4/Vtb > $1_$4.log 2>&1; echo "$1 $(grep LOCKSTEP $1_$4.log) $(grep -m1 MISMATCH $1_$4.log | cut -c1-120)"; rm -rf obj_$1_$4; }
for s in 1 2 3 4 5 6; do run clean dut0.sv 0 $s 20000 & done
wait
for m in 1 2 3 4 5 6 7; do run mut$m dut$m.sv 0 2$m 20000 & done
wait
for m in 8 9 10 11 12 13 14 15 16 17 18 19; do run mut$m dut$m.sv 0 2$m 20000 & done
wait
export GD=-DGOOD
for s in 41 42 43 44 45 46; do run good dut0.sv 0 $s 30000 & done
wait
for m in 1 2 3 4 5 6 7; do run gmut$m dut$m.sv 0 5$m 20000 & done
wait
for m in 16 17 18 19; do run gmut$m dut$m.sv 0 5$m 20000 & done
wait
for m in 8 9 10 11 12 13 14 15; do run gmut$m dut$m.sv 0 5$m 20000 & done
wait
