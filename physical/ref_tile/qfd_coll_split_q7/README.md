# qfd_coll_split_q7 -- Q leaf successor of q6/q6w (QW-COLLQ6 10-20 21:50; parallel pair q7 main / q7w fallback)

Predecessor verdicts (ot-agidock128 ref_gate/qfd_coll_split_q6{,w}-20261020-083557, terminal; local clients died):
- q6 r2 (q6 geometry, E stack x=129.6, native released): GRT-0232 overflow 605 (M4 549); congestion.rpt hotspots at
  x~120-140 (std channel between the stacks). CTS spread n/a in gate (no gate_result r2).
- q6w r2 (q5w geometry, E stack x=172.8, all-native nets frozen): GRT overflow 0, CTS TT/FF spread 42.2/37.0 PASS; GRT
  parasitics: SS setup -284 -> -258.65 (out_data D; SS = sensitivity only), FF hold -274 (u_sd SRAM wd_in) -> -200.03
  after 3 repair rounds (2602+1853 hold buffers), residue ~1000 endpoints on native flop D pins (u_native.c2802/D)
  behind FROZEN nets; then DRT-9419 "Inst _09139_ not found" in the parasitic update -> stage abort.
- both: TIELO net g_pf_fan32.u_pf/_409_ unsplit with 1345 loads (floorplan repair_tie_fanout split TIEHI only).

Structural change: q6w geometry (route-proven GRT0) + PRE_GLOBAL_PLACE native_release_tie.tcl: release
dont_touch on native + tie cells (no net freeze), re-run repair_tie_fanout, report the largest non-clock net.
Function unchanged; equivalence = standard RTL vs netlist. Zero added cycles.

## SAFE-DESIGN checklist
1 Pins: RTL registers every pin; reset face leaf u_rsf 2 stages + 2 kept relays (rst_n 2 raw sinks) -- PASS (r4)
2 Reach: tile <= 260 um/side -- PASS(geom); post-GRT native reach audit owed at route
3 Fanout: census r4 PASS max32 (gate native_census re-checks); tie net 1345 -> re-split by hook -- fixed
4 Depth: native LAT7 adder 288 ps / 9 levels -- PASS(model)
5 Storage: rings/skew lines in 12 SRAMs; no flop array > 2 kb -- PASS
6 Floorplan: macros on the 43.2 lattice, two N-S stacks (W x=43.2, E x=172.8), 95 um std channel; abutted 0-um macro channels WARN (pins face the channel); fill 40% WARN (macro-bound)
7 Clock: balanced symmetric spine (OT_SPINE SYM/SAFE_BALANCE/MACRO_LEAF), single region; q6w measured 42.2/37.0; io_hold_margin 0.03
8 Schedule: static; zero data edges; reset release +1 edge uniform -- PASS
Benches: bench4 r4 gold unit+prod rc0 (V5.050); mutants SBANK/OWNER/GATHER caught; OT_COLL_SPLIT_MUT_RERR SURVIVES
(no bench case exercises the C R-meta err bit) -> covering case or fail_witness_waiver owed before submit.
