# qfd_coll_split_q6 -- Q leaf successor of q5 (QW-ORPHANS2 10-20)

q5 gate FAIL (2 fail / 7 warn): (a) reset_landing: rst_n reached 4 raw sinks (two face leaves u_rs/u_rs2, census r3);
(b) GPL RSZ-3006: timing-driven repair could not buffer native adder net ...g_st[3].g_lane[3]...u_native.n1957
(OAI311xp33 driving 25 native loads, every native cell (* dont_touch *) from the generated netlist; ODB-1211).

Structural fixes (both in q6):
1. RTL r4 (rtl/rom/ot_coll_tp8_split_native32.sv, default; r3 under OT_COLL_Q_RST_FACE2): ONE 2-flop face leaf u_rsf
   (rst_n = 2 raw sinks) drives only two kept registered relay copies u_rs / u_rs2 (ID 208/209); every reset consumer
   releases exactly one edge later than r3, uniformly (equal depth; no data edge; static schedule unchanged).
2. PRE_GLOBAL_PLACE native_size_release.tcl (r2): dont_touch released on ALL native cells (r1 kept flops: RSZ-3006 on n1962 with
   dont_touch flop loads), so repair may size/buffer and CTS may connect native flop clocks; census re-checked on the GRT ODB.

Gate r1 (09:00): reset_landing PASS (rst_n 2 raw sinks); placement FAIL as above -> r2 hooks.

## SAFE-DESIGN checklist
1 Pins: RTL registers every pin (q4 lineage); reset lands at the face in 2 registered stages (u_rsf) -- PASS (fixed)
2 Reach: tile <= 260 um/side; gate native audit on the GRT ODB -- PASS(geom)
3 Fanout: census r3 max32/0 viol; r4 census (rs_f 2 loads, rs/rs2 same loads as r3 rs/rs2) in pending_results -- PASS(r3), r4 pending
4 Depth: native LAT7 adder 288 ps / 9 levels -- PASS(model)
5 Storage: rings/skew lines in 12 SRAMs; no flop array > 2 kb -- PASS
6 Floorplan: q5 geometry (abutted N-S stacks on the 43.2 lattice; 0-um channels between abutted macros WARN), fill ~40-42% WARN (macro-bound) -- WARN
7 Clock: balanced symmetric spine (OT_SPINE SYM/SAFE_BALANCE/MACRO_LEAF); io_hold_margin 0.03; verdict on TT/FF spread <= 80 -- gate
8 Schedule: zero data edges; reset release +1 edge uniform -- PASS
Benches: r4 8-die gold unit+prod + 6 mutants V5.050 (pending_results). OT_COLL_SPLIT_MUT_RERR survived r3 (bench never
exercises the C R-meta err bit): needs a covering case or a fail_witness_waiver before submit.
