# s81dvbk_sq_hq3 -- TOPK selector quarter, HIERARCHICAL native-census-clean successor (dsdv_bksel_q, S81-TOPK7 2026-10-20)

Opt-in `OT_S81PH_SEL_HQ`: dsdv_bksel_q binds `dsfd_selt_q_hq` (rtl/dsrom_sys/s81_ph/ot_s81ph_hq_tile.sv,
selector_native/ot_s81ph_hq_slice.sv, selector_native/ot_s81ph_hq_parts.sv). Default RTL unchanged.
Geometry and clock = s81dvbk_sq_succ4 (324 x 540, 16 p192 macros on the 43.2 lattice, K16 regional roots).

Why: the monolithic quarter family is structurally dead. succ3 and sq_reg hit GATE_STALL. succ4 and succ4k8 stalled in
hold repair, and the placed census showed 1,778 nets over 32 loads. The OMERGE canonical synth census FAILED 741
drivers over 32 (the rst_n flop alone drove 10,760 loads; evidence 89ba149e4).

## Structure (exact; 0 added edges)
- Reset: the kit lands `rst` at the face in 2 balanced stages (8 first / 160 final kept copies,
  reset_relay_split max_loads 32). The datapath and payload registers carry no reset. The 16 hist banks land their own reset.
- Histograms: 2 x 8 instances of the hardened hist32 bank (`ot_s81ph_native_sel_hist_bank`, TOPK5 R3 gate PASS max25),
  wired with no edges added. Each bank gets its own seg_clr copy (clear) and command copy (gsel). gbin is a combinational
  OR-join of the registered bank outputs. busy is recomputed exactly at the parent.
- Packers: 6 bit planes of the unchanged pack (FAN32 + ACC32). Each plane has kept select copies (one for the prefix,
  one for the gating). Under HQ only the ACC32 lane valid bit is reset. frun = lane copy 0.
- Wide selects use registered one-hot AND-OR with kept copies (<= 27 bits each): r1_d, the o0 output stage, pend
  (delayed capture + bypass, exact), and mem_wdata (selects built from distinct plane flops).
- Every hot control has kept copies: seg_clr (48, two sources), state decodes ph/sw_st/sw_k, a_end, sw_seg, rem,
  head-full, tsw, sw_T[15:8], the key sign bits, c_T/c_Bt (per 4 lanes), c_cg/c_fg (per bank), the lane type decode
  (4 distinct decodes that differ only on illegal types), cur, and the FQ/OFQ pointers (two-hit showahead store).
- SRAM: each depth bank of line macros has its own write-data register copy, launched beside its macros.

## Safe-design checklist (owner 10-19)
1. Pins: PASS. Pin flops are in source (u_in s0, QIO cq0/cq, sq/sq1, oq/oq1). The reset lands in 2 kit stages.
2. Reach: PASS by construction, unchanged from succ2/succ4 (macro capture to band is about 300 um, under 405). The gate re-measures it.
3. Fanout: FIXED in RTL. The native census on the mapped netlist must show max <= 32 before the gate (see results/arch/s81_topk7_1020/synth).
4. Depth: PASS. Wide muxes are now registered one-hot AND-OR; there are no new combinational levels on any stage.
5. Storage: PASS. FQ/OFQ are in 10 SRAMs and the line pool in 6 SRAMs; pend / o0 / wdata copies are pipeline registers, not indexed storage.
6. Floorplan: same as succ4 (lattice, halos, band). Fill is WAIVED with the succ4 reason (macro/pin-escape bound).
7. Clock: K16 regional roots (succ4 recipe). The gate must show pin-flop spread <= 80 at TT and FF. io_hold 0.03.
8. Schedule: PASS. The design is static and adds 0 cycles: the cycle-exact production bench (tb_bk_layer, compiler
   expected edges unchanged) passes. INDEXED13's 1037 reserved cycles are unchanged.

Benches: results/arch/s81_topk7_1020/run_hq_suite.sh (Verilator 5.050). 5 positive benches PASS; identity / corrupt /
early FAIL; 4 causal HQ mutants FAIL (OT_S81PH_SEL_HQ_MUT 1..4).

## Collected HQ3 admission (Codex 10-20)

Native main360c643 mapped census PASS: 220,623 dynamic roots, max32, 0 violations. Actual seven loaded Liberty files and netlist SHA256 retained under results/arch/s81_topk7_1020/hq3/census. Synthesis area105,912.99 um2 includes 66.3k macro area; standard-cell area39.6k. Existing outline324x540 gives60.5% total fill and about36.4% standard-cell-only occupancy. Pin/macro-escape geometry remains binding; fill reason retained. No physical timing or reach closure is claimed before gate.

All five archived Verilator5.050 build manifests match the collected RTL exactly. Five positives pass; identity/corrupt/early and four causal mutants on both indexed13 and legacy fail. Compiler output edge expectations unchanged (+0 cycles). hq1 artifacts untouched.
