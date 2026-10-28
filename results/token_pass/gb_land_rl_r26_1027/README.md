# S81-CORES-R26/GB: GB return-lane landing epoch = BENCH GAP (hardened reset landing missing), not a die fault (Tue Oct 27 18:57:56 PDT 2026)

COORD add-on (10-27): "GB return-lane landing epoch fails on 6/6 lanes on real b178 logic (claude/tok17-gb-1027@3795d35a1c),
reset releases 2-3 edges before the clock gate opens; pad the reset stations so R0 == G, do not raise K."

Finding (CHECKED, this dir): the tok17 cone bench instantiates the RTL dsfd_dvland_70 (rs straight into ot_s81_land).
The HARDENED view s81dv_land_70 lands rs in 2 plain ck flops (rs__ot_rl0 -> rs__ot_rl1) before the core
(physical/ref_tile/s81dv_land_70/spec.json reset_landing {enable, stages 2}, COORD HANDOFF 0jz 10-19), and the die
calendar prices exactly that: bind table landing_reset_stages dsfd_dvland_70 = 2 (tools/s81_dv/dv_bind.py
dr_ = rdep[rleaf] + RL; results/arch/codex_s81_frame_bind_impl_1021/bind_table_frames72.json).  That is why the netlist
landing rs is 2 stations shallower than "R0 = G + (N mod 2)" (tok17 reset_depths.txt: land-gate = h - 2 on all 6 lanes:
odd-N 0L01/0L02/0R02/0R03 -1, even-N 0L03/0R01 -2).  Die sims must use tools/s81_dv/die_sim_wrappers.py for this reason
(STW-S81c-RTLGAP 10-22); the cone bench did not.

Vehicle: tools/s81_dv/tokfunc/run_ret_cone_rl.sh SRC OUT RL = tok17 run_ret_cone.sh with dsfd_dvland_70 wrapped by RL
ck flops on rs (die_sim_wrappers / ot_pin_regs.tcl OT_RST_LAND rule; instance u kept so the tb probes are unchanged).
Same die_b178.v / land plan / masters (sources.sha256), die K straps unchanged (2,1,2,2,1,2).
- RL=0 (control = tok17 vehicle): run_tt.rc.txt byte-identical to tok17 cone/run_tt.rc.txt: land_fault=1 FAIL.
- RL=2 (hardened view): TT PASS + FF PASS, 6/6 lanes 44/44 in order, land_fault 0; latencies 23/40/36/27/38/48 cycles
  (0L01/0L02/0L03/0R01/0R02/0R03) = tok17 K+2 what-if contract latencies.  mutsel control: FAIL (2 lanes fault + -1 latency) = caught.
- RL=4 / RL=5 (= the ordered +2/+3 reset padding ON TOP of the hardened landing): no fault, but data latency +1 on the
  F=1 lanes 0L01/0L03/0R01/0R03 (24/40/37/28/38/49): the padding is NOT boot-only, it moves the contract latency.
Conclusion: R0 = G + (N mod 2) already holds in silicon; NO die / reset-station / K change.  Do not pad.
Landing window: unchanged die => land plan rows (p4l land_plan.json) E=2 D=4 K=2 window_ok True for 0L01/0L03/0R01/0R03
(tt_ff_spread 77.8/165.8/75.2/168.4 ps), 0L02/0R02 die_v K strap 1 (E=1) -- no recheck needed beyond the existing rows.
TOK-ALL-18: rerun the six-frame slice bench with the die_sim_wrappers filelist (or this RL=2 wrapper) for every
hardened landing/view; use latencies 23/40/36/27/38/48 for the u_s_0S return lanes.
