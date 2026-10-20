# hbm_su_pg_stream_b_safe3_1019 -- PGSTREAM-B tile on the SAFE3 source (HBM d4g LIGHT SU slice stream sibling)

Owner LEAD2-HBM/L2H-PGVM 10-19, branch claude/l2h-pgs3-1019. Spec generator tools/ref_tile/specs_hbm_su3/mk_pg_stream_b_safe3.py.
Source evidence: results/rtl/hbm_pgstream_safe_1019/safe3/README.md (bench_s3 3 PASS / 8 FAIL on Verilator 5.050; map c4751
0 roots > 32, 0 inputs reaching logic, 0 outputs from logic, 10,098 FF, 4,351 um2).
Top `ot_hbm_su_static_pg_stream_split_safe3`; parallel successor of hbm_su_pg_stream_b_safe2_1019 (gate 121732 live) that
fixes the SAFE2 native audit 78b77c1ff (596 inputs reaching logic, 42 outputs from logic, inject sq roots 42).

## SAFE-DESIGN checklist (owner 10-19)
| # | item | result |
|---|---|---|
| 1 | pin regs + reset landing | FIXED: su_wq / vmr_cmd captured at the face (+1 serial edge, priced LH-REPRICE3), ij_* straight from region flops, lg_fault output flop (+1 stream edge); mapped boundary check 0 / 0. Reset: kit 1 face flop + source-owned epoch-exact tree (as SAFE2) |
| 2 | reach <= 405 um | 216 x 259.2 outline, diameter 475 > 405: single-cycle paths local to the W serial / E stream halves; SAFE2 placed audit max direct pin pair 165 um. CHECK at gate |
| 3 | fanout <= 32 | FIXED: map c4751 0 roots > 32 (max 32), incl. the inject_q sq roots (registered one-hot selects, own-bit regions) |
| 4 | depth | input capture removes the pin->hold-mux paths; inject_q select is one AND-OR level after a register |
| 5 | storage | unchanged: bridge banks < 2 kb each, no new delay lines |
| 6 | floorplan | WAIVED pin-bound (as b_1019 / SAFE2): ~3,580 pins, ~4,351 um2; 216 x 259.2 keeps W/E <= 6 pins/um; no macros, one std-cell band |
| 7 | clock | two regional roots (clk_ctl W, pg_clk E), seam windows request 4q/2q, return 2q/4q, inject 3q/7q + 4 CDC synchroniser groups (as SAFE2; SAFE2 gate 121732 CTS: placed setup +133 / hold +35 ps, XCLK 0 violating); io_hold_margin 0.03 |
| 8 | schedule | static: inject +1 stream edge (SAFE2), SU request +1 serial edge, lg_fault +1 stream edge -- all in the LH-REPRICE3 input notes; reset release constant unchanged |

## Tool note
Same branch-local CDC helper fixes as SAFE2 (cdc_sync_constraints keep_hierarchy unset before flatten; ot_cdc_flow_names '/' -> '.'):
needed on main before submit_exact / the closure daemon judges this kit.

## SAFE2 kit notes (base)
Top `ot_hbm_su_static_pg_stream_split_safe2` (same ports as the b_1019 top), 216 x 259.2, two regional roots
(clk_ctl serial, pg_clk stream), banked 3:4 seam inside (seam_windows), four declared CDC synchroniser groups.
Parallel alternative to the b_1019 kit (gate95463 WARN but NOT submittable: its 3-stage clk_ctl reset landing releases
the stream root one stream edge early -- tb_hbm_su_pg_stream_kitland lockstep FAIL, seam windows 1q vs the declared 4q/2q).

## SAFE-DESIGN checklist (owner 10-19)
| # | item | result |
|---|---|---|
| 1 | pin regs + reset landing | FIXED: every data pin has its register in RTL (pin_regs opt-out with that reason); inj_rd / inj_addr now captured per inject region on pg_clk (SAFE2 r5, +1 stream edge, priced). Reset: kit lands each reset port in ONE face flop (reset_landing.stages 1), the source owns the rest (rst_n 2 serial stages; bridge_rst_n kept tree: serial stage A -> 129 terminals, stream feeder F -> P -> 86 terminals), both roots release on the same coincident edge 12q after the face flop |
| 2 | reach <= 405 um | outline diameter 475 um > 405 (216 x 259.2): single-cycle paths are local to the two regional halves (W serial / E stream); CHECK at gate on the placed census |
| 3 | fanout <= 32 | FIXED: native TT map r7 = 0 roots > 32 (max 32; r3 had 14, max 1,726): reset trees, replicated leaf/tap sync stage 2, tap select regions, inject regions with own counters / decode, {bad} flag split per group (pairwise) |
| 4 | depth | unchanged decode depth; inject decode now starts from local capture registers (was the input pins) |
| 5 | storage | unchanged: bridge banks < 2 kb each, no new delay lines |
| 6 | floorplan | WAIVED pin-bound (as b_1019): 3,580 pins, ~4,185 um2 synthesized; 216 x 259.2 keeps W/E <= 6 pins/um. No macros, one std-cell band |
| 7 | clock | two regional roots (clk_ctl beside the W slice face, pg_clk beside the E LG face), related 3:4 crossings declared: seam windows (request 4q/2q, return 2q/4q, inject 3q/7q) + cdc_synchronizers (pg_fault_level, pg_leaf_reset, pg_tap_reset, bridge_stream_reset); io_hold_margin 0.03; gate rule pin-flop spread <= 80 TT+FF |
| 8 | schedule | static: +1 stream edge on the inject path (compiler issues inject addresses one stream edge earlier; LH-REPRICE3 input note); reset release constant unchanged (12q after the face flop, both roots) |

## Tool note
tools/ref_tile/cdc_sync_constraints.py (this branch): the CDC lint now unsets keep_hierarchy before its logical flatten
(kept region / replica cells were 'unexpected unmapped cell'); kept replicas of one register are one register in the
lint, synthesis keeps them apart. Needs the same change on main before submit_exact / the closure daemon judges this kit.


CODEX 10-20 pre-gate native check (helper-only retry after CTS enumeration cap):
Exact failed gate mapped netlist SHA and audit hashes in
results/rtl/hbm_pgstream_safe_1019/safe3/mapped_gate_all_drivers.json.
24,455 nonclock/nonconstant roots, 10,622 FF, max32, zero drivers>32;
includes every reset/port/comb/FF with BUF/INV transparent. All tile RTL,
params, outline, clock budgets and reset calendar unchanged. Registered
boundary proof remains source-pinned SAFE3 (0input logic/0output logic),
216x259.2um diagonal<405um; source per-region stores remain <=2kb,
no runtime indexed large FF store. Pin-bound fill waiver unchanged (W/E
1183/1117 bits require >=197um at6/um). Added cycles0.
CDC verification now applies ALL exact constraints before querying each
pair max/min; same bounds and finite-path rules (tool c9601c494,
Gate-Rule neutral);4batch+12CDC+6mixed actual graph tests PASS fleet5.
Previous gate FAIL remains preserved65cea4293; not physical qualification.


CODEX 10-20 batch4 terminal review (01:07 gate): WARN0FAIL, CTS744s,
trialGRT199s overflow0, M2max28.39%. Pin spread pg_clk TT38.8/FF38.0ps;
clk_ctl TT57.8/FF55.4ps. CTS TTsetup+150.43ps, representative hold+29.5ps
(gate evidence only; final SS/FF signoff belongs to route). Clock insertion
pg_clk TT340.7/FF285.4, clk_ctl TT330.8/FF279.2 guidance only.
Actualfloorplan+density PNGs viewed: all perimeter pins, no macros,
216x259.2um aspect1.2, no stdcell islands/corridors; two diagonal register
bands plus boundary mass, clock entries beside lower root groups. The
9.4% fill is pin-bound (W/E1183/1117 pins need>=197um at6/um), unchanged
waiver. Native source24455roots max32 zeroover32 including reset.
Exact CDC/SEAM finite proofs PASS: return1028/inject132/request1200;
streamreset3, pgfault1, leafreset1, tapreset1. Behavioral3PASS/8mutFAIL
witnesses committed;0input/output boundary logic from SAFE3 sourceaudit.
NativePG raw intermediate CTS/GRT audits both18264 unbound hold-cell
PGterms; infrastructure owner proved protected0/fixed0 and ordinary
in-memory global_connect clears0 on both frozen checkpoints (inputSHA
unchanged). This is normal intermediate birth phase, not final PG closure;
final route6_final must still pass nativePG. Raw audits retained unchanged.
No mapped-cell functional/equivalence claim: pureRTLbench evidence only;
current imported DFFASRHQN truth-model issue does not alter nativecounts.
