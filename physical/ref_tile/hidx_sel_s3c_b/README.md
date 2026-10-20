# hidx_sel_s3c_b -- ctl tile ot_hidx_s3_ctl of the landed IDX selector cluster
L2H-IDXSEL s3 (LEAD3-HBM route B, 10-19/20). The HBM IDX selector becomes an lp.py LANDED CLUSTER (die master
ot_hbm_idx_selector_s3, port list == the die's selected-only master ot_hbm_idx_selector_static_sel): ONE hardened quadrant
tile ot_hidx_s3_q used x4 + this ctl tile ot_hidx_s3_ctl, wires-only flat parent ot_hidx_s3_flat ->
rtl/hbm_accel/index/sel_s3/lp/ot_hidx_s3_flat_lp.sv (tools/landed_parent/lp.py, spec tools/landed_parent/specs/hidx_sel_s3.json:
5 regions, 20 landed crossings, D 4 / E 2, +3 edges each, reschedule mode because ctl <-> quadrant is a loop).
Predecessors: s1a/s1b GATE_STALL in CTS hold repair (one clk_ctl root, 42,772 sinks, 18-23k hold endpoints);
s2a/s2b (five roots inside one leaf, ~7k unlanded inter-root crossings) FAIL at floorplan (IO-domain coverage).
Schedule (tools/hbm_idx_static_calendar.py table registered_s3): sel_in 7 (op word: ctl pin flop + ctl out flop + landing 3 +
quadrant pin copies + P2), sel_in_line 2, sel_out 1, sel_choose_rt 8 idle edges after every op5 run (threshold back to the
quadrant 12 edges after the deciding histogram read, ties 13; flat core 3 / 4). IDX frame 1411 -> 1433 edges (+22, +1.56%).
Benches (Verilator 5.050, fleet): rtl/test/hbm_idx_static/run_selector_s3.sh (full shape, crafted margin frame + 3 historical
frames, selected stream exact vs gold): m0 PASS; d1 d3 d5 d6 rt7 dr3 l1 l2 FAIL (witnesses results/rtl/hbm_idx_static/selector_s3/sel);
lp lockstep + audit rtl/hbm_accel/index/sel_s3/lp/ot_hidx_s3_flat_lp_bench.sh (MUT 1 2 4 5 FAIL);
full-shape scheduled proof rtl/test/hbm_idx_static/run_scheduled_s3.sh (IDX_SCHEDULED_GATE_PASS; see results/rtl/hbm_idx_static/selector_s3).

Geometry (b): 54.0 x 64.8; S face = die control ports (op/pass/addr/k, clk, rst_n, fault), W = ret/ties/qf of the W
quadrants (u_q0, u_q2), E = the E quadrants (u_q1, u_q3), N = cw / thr (shared write rings). Std cells only (~0.5k flops).

## SAFE-DESIGN checklist (owner 10-19)
1 Pins: PASS -- op/pass/addr/k land in cw_r / k_r, ret_<q> / qf_<q> in a_ret / a_qf (input pin flops); cw is an output
  flop after cw_r, thr / ties_<q> / fault are registers; rst_n -> ot_rst_relay (2 sync + region stage).
2 Reach: PASS -- tile <= 64.8 um; all long ctl <-> quadrant distance is on the landed ring -> read multicycle in the parent.
3 Fanout: PASS -- cw / thr each feed one shared write ring (4 slots); hrd sums read a_ret once.
4 Depth: PASS (expected) -- stage B = 4-way 16-bit sums, C = 16-bit compare + subtract + threshold mux (flat core logic).
5 Storage: PASS -- no arrays; the op5 outstanding count is a 7-bit counter (no delay line).
6 Floorplan: PASS -- std cells only, outline sized for util ~0.4-0.5 from the flop count, aspect <= 1.25.
7 Clock: PASS -- one small root (ck_ctl region), every crossing landed in the parent.
8 Schedule: PASS -- the choose pipeline runs on the returned stream (tags travel with the histogram read); priced as
  sel_choose_rt 8 in registered_s3.
