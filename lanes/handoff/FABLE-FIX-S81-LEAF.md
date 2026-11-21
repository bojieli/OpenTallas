# FABLE-FIX-S81-LEAF handoff (Fable, restarted 2026-11-20 21:20 PST; owns ot_s81sl_leaf__t*, rep t39)

Read order: this file, then lanes/posts/FABLE-FIX-S81-LEAF.md. The 11-19 lane sections are in lanes/handoff/archive/FABLE-FIX-S81-LEAF-1119.md (moved so the owners sweep does not credit this lane with every type they name).
Work root: epyc7 /srv/opentallas-scratch2/claude/fable-fix-s81-leaf-r3 (B). Lane clone B/repo (main 1b57af8f34, sparse). Nothing pushed yet.

## Finding (post-hook, STA re-read of the b05c baseline 4_cts odb; B/whatif/sta)
- The baseline kit is D8i (b05c). Its SDC charges a per-tap window of 68-208 ps on every cross-tap pair. That window makes 13,788 of the 14,251 cross-tap hold ends (463 remain with the launch window at 0).
- J5 t39 carries windows of 10-82 ps (config diff D8i -> J5: OT_TAP_WINDOW 208 -> 82, OT_HOLD_OUT_MIN 68 -> 10, max transition 320, hold setup guard -42; RTL the same but 3 relays).
- Same CTS DB under the J5 SDC (j5sdc.hold.tsv / j5sdc.setup.tsv): hold 5,966 ends (cross_tap 3,173 ws -155, port_out 1,584, port_in 1,167, same_tap 42); the 5,583 ft station-chain ends are gone. Setup wns -254, 312 ends, 146 under -42.
- clk_t6 at (971,406) is the only tap of the vp hig station bank (8,200 flops in 225 x 280 um): 7,040 sinks, window 78. It is in 2,010 of the 3,173 cross-tap hold ends and captures 255 of the 312 setup ends.
- Setup classes, ranked: (1) leaf reset bit u_lpad_leafdn_i0.q[594] -> crr_* / u_vs, 500-900 um in one cycle (-254); (2) vp driver_dodd_q -> vp_cf flop memory, 193 ends, -178 (q1r mux then about 300 um to cf, capture on t6); (3) u_rrl_278 -> cland_fstart_ft4_o -157; (4) cst_swr -> u_vs core pins, 40 ends, -146; (5) vp src -> src on t20 -> t6, 46 ends, -64.

## Proof p1 (running)
- B/p1 = pristine J5 t39 kit (kw43 224567138ab attempt_3 gen copy) plus:
  - reset_leg_plan rows (B/leg/j5/plan1_nolk.json, geometry = J5 a3 3_3_place_gp): relay_depth u_lpad_leafdn_i0.d bit 594 D 4 and u_u_lf1_u_vp_u_rr.rst_n_in D 1 (+4 reset cycles), relay_split 4 flops / 17 copies, 27 relay_sites. Applied with B/p1/prep.py (after RESET-RELAY-GEN prep10.py). Same-edge stages, no latch: the hops are 238-268 um.
  - config.mk: OT_TAP_PAIR_UM 200, OT_TAP_PAIR_OVERFULL_GROW 0.3, OT_TAP_PAIR_CAP 1500 (originals kept as *.orig_p1).
- Launch B/p1/launch.sh (ot-run epyc7, run_kit.sh route 48 8), log B/p1/run.log, unit oth-ubuntu-2178345-1795239930.
- Control = the J5 wave row t39 a3 (epyc7 ot-jobs/ot_s81sl_leaf__t39-route-loved-redfish-1218124-1795237605).
- Read at CTS: 4_1_cts.log OT_TAP_PAIR / OT_CTS_POST_TIMING, 4_cts_post_hook.rpt, hold_gate.log, pregrt_ff_hold.log class before/after + hold_cells; then GRT it5/it10 overflow.

## Sibling rows (running)
- reset_leg_plan on the newest placed kit of 69 leaf / kv_leaf types: each gen host, /srv/opentallas-scratch2/claude/fable-fix-s81-leaf-r3/sib/<type>/{plan1.json, plan1_nolk.json, report*.json, SOURCE}; batch log sib/otrun.log; list sib/leaf_kits.tsv.
- Rows are provisional until p1 reads at CTS.

## Open
- dodd -> cf (class 2) has no row: needs a cf write register in ot_s81sl_vp.sv (+1 edge on the cf write) or cf placed at the driver. Not started.
- cst_swr -> u_vs core pins (class 4): path not read in detail (report_checks to a core pin failed in my script).
- The t6 bank needs tap ports of its own (TAP-GRID-2130); p1 only lets t6 keep its partners.

