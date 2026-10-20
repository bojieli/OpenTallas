# hcoll_issuer_r128v7 / hcoll_issuer_r128v7b -- 128-row COLL issuer leaf, v7 core (SRAM loop tables)

HBM-COLLQ3-V7 10-19. LEAD3-HBM decision "SRAM v7" (SAFE-DESIGN item 5, no waiver): the ROWS-128 issuer leaf
`ot_hgi_coll_issuer_m_r128` (hard child of the SAFE q2/q3 COLL landed parents `ot_hfd_coll_{q2,q3}_lp_ars`, element
`ot_hfd_coll_q3_hard_v8x` / `ot_hfd_coll_q2_hard_v8g`) is rebuilt on the v7 core instead of v6's 16 kb of runtime-indexed
flop loop tables. Same leaf name and instance name (`u`): the parents need NO re-pointing.

- Core `rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_static_issuer_v7r128.sv` (header = structure + the two programme
  constraints). Leaf `ot_hgi_coll_issuer_m128v7` = `ot_hgi_coll_issuer_m #(ROWS 128)` port for port, edge for edge.
- Macros: data 3 banks x 2 x `ot_sram_1r1w_128x256_m1_r2c2_p192_mir` (existing QW-SRAM3 / COLL safe-pins macro);
  metadata 4 x `ot_sram_1rw_128x64_m2_r2c2_p192_mir` (new, `tools/mem_compiler/build_coll_iss7_1019.py`, same p192 recipe,
  on track in R0/MX/MY/R180 per `tools/check_macro_track_alignment.py`).
- Programme target (`ot_hgi_coll_static_program_target.sv`): ROWS 128 now sets `issuer_start_pc` at descriptor accept (as
  ROWS 256 already did) so v7 primes its lookahead; v6 reads start_pc only on start, so v6 edges are unchanged. This
  changes the ROWS-128 fj leaves (hcoll_fj3_r128w / hcoll_fj2_r128w re-gate from this branch).
- Kits: `hcoll_issuer_r128v7` (main, single abutted 6-macro data stack, 302.4 x 561.6) and `hcoll_issuer_r128v7b`
  (PARALLEL fallback outline, two 3-macro columns, 432 x 345.6). Same RTL; bind the first to close, cancel the other.

## Benches (Verilator 5.050, fleet)
- `run_issuer_v7r128_miter.sh`: core v7_r128 vs v6 #(ROWS 128) AND leaf m128v7 vs issuer_m #(ROWS 128), every port every
  edge, 600 random programmes over all 128 rows; mutants reload / nofwd / swap must be rejected
  (witnesses `results/rtl/hbm_coll_iss7_1019/witness/`).
- `run_coll_lp_ars_all.sh q3|q2 eq`: the SAFE parent (this leaf inside) == v8x / v8g #(AR_ITER 1, ROWS 128) (v6 issuer)
  under the AR scripted programme + 3 EQ mutants; `lp` and `rs` parts re-run with the new leaf.
- Results: see `results/rtl/hbm_coll_iss7_1019/README.md`.

## SAFE-DESIGN checklist (owner 10-19)
1. Pins: PASS. cfg/start/start_pc registered in RTL (PIN_REGS 1, as the closed issuer); every output flop Q (raw busy =
   busy_c | start_q, as closed); rst_n loads one synchroniser; reset_landing 2 stages in the kit.
2. Reach: PASS. main: data stack rd_out W face (x 172.8) -> bank data regs -> uop_d1 W pins ~175 um; metadata column
   (x 43.2..81) <-> control band <= 130 um; fetch_pc -> farthest data macro address <= ~250 um. b: column-2 rd_out ->
   uop_d1 W pins <= ~305 um (bank data reg beside the macro, one more flop at the pin). All < 405 um.
3. Fanout: gate-checked. `take` (comb from flops) selects ~150 bits (4 x 7-b addresses, CT/CN records, L1 data) and
   arrives ahead of the macro data; uop_v masks the 1,536-b stream through a synthesised buffer tree on a flop->AND->flop
   path (closed-leaf structure, not a critical cone). start -> L1 reset is a registered start.
4. Depth: PASS by construction. Loop paths: metadata macro Q (TT 323 ps) -> 2:1 -> macro address (setup 28 ps);
   decision = 32-b compare of two flops; counter forward = 32:1 x 32 b from a flop index. No in->out comb path.
5. Storage: FIXED (the v6 failure). Data 6 x 128x256 SRAM; metadata 4 x 128x64 SRAM. Remaining flop arrays: row-valid
   5 x 128 b (single-bit reads), loop counters 32 x 32 b (1 kb), cfg staging 2 x 512 b (fixed-slot writes); each <= 1 kb.
   (v6 ROWS 128: meta 8 kb + rowloops 4 kb + rowcm1 4 kb runtime-indexed.)
6. Floorplan: macros on the 43.2 lattice (stack origins (172.8, 43.2) [b: + (302.4, 43.2)], abutted pitch 80.496 =
   height + 0.024; metadata column origin (43.2, 216.0) [b: (43.2, 129.6)], pitch 23.808); macro pins <= 5.21/um
   (p192); 34.8 um E channel [b: + 34.8 um inter-column channel]; W face uop_d1 1,536 b: 2.7/um [b: 4.4/um]; aspect 1.86
   [b: 1.25]; one connected std-cell band. Outline is macro/pin-bound (10 SRAMs + 1,536 W pins); std-cell util from the
   gate synthesis is recorded in the gate summary below.
7. Clock: one clock (clk_control) for logic and all ten macros; TT/FF pin-flop spread <= 80 from the gate;
   route io_hold_margin 0.03.
8. Schedule: no added edge on any port (cycle-exact to v6 #(ROWS 128) at core and leaf level) -> 0 cycles DS / 0 cycles
   Qwen per token; constraints (a) start_pc stable >= 4 edges before start (programme target sets it at descriptor
   accept, >= 130 edges before launch) and (b) loop ids < 32 (compilers map loop ids densely) are proven on the parent
   programmes by the lockstep EQ.

## Gate
(summary appended by the lane after the --cts gates)
