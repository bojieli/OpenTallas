# hbm_su_pg_stream_b_safe2_1019 -- PGSTREAM-B tile on the SAFE2 source (HBM d4g LIGHT SU slice stream sibling)

Owner LEAD-HBM/LH-PGVM2 10-19, branch claude/lh-pgvm-pgsafe-1019. Spec generator
tools/ref_tile/specs_hbm_su3/mk_pg_stream_b_safe2.py (derived from the b_1019 kit spec). Source evidence:
results/rtl/hbm_pgstream_safe_1019/safe2/README.md (benches bench_r7, native TT map map_r7).

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
