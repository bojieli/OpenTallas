# HNEXT.ATT4 cluster-leaf successor of the P3 shared attention merge (claude/hnx-att4-leaf-1020, 2026-10-20)

Lane HNX-SM4/ATT4. Next-release HBM die (P=3), below the release gates. The flat tile (spvm) is critical-reviewed HBM
work: the coordinator reviews gate PNGs and the checklist. No REVIEW.json and no submit from this lane.

## Why the `_nf` tile failed (hnx_rp3a3_spvm_safe_nf, gate ot-agidock128 ref_gate/hnx_rp3a3_spvm_safe_nf-20261019-115212)
- **Clock.** One root fed 18,542 sinks over 432 x 432 um. The entry was a clk pin on the E face, low corner, far from
  the register mass (the central band and the N/S pin rows). Measured pin-flop spread TT 127.1 / FF 114.1 ps (limit 80).
  Insertion was TT 509..699 and FF 414..583 ps.
- **GRT rc 137.** This is SIGKILL from the gate's 4 h `GATE_STALL` watchdog ("exceeded 14400 s"). It is not an
  out-of-memory kill and not an overflow verdict. GRT kept re-entering 30-iteration congestion loops: grt.log shows
  repeated extra iterations 1..15/30 and NDR dropped on every clock net "to reduce congestion".
  M6 was 100 % derated (cap M5).
- **Floorplan cause.** 18 SRAMs sat in six abutted 3-stacks. Each hnx_sram_1r1w_128x256_r43 carries 393 live pins on
  its 43.2 um W face (rd_out 256, wd_in 137, control) and 119 live wd_in on its E face (the 256 w_mask pins are tied).
  That puts about 9.1 live pins/um on the column channels. Every adder reads word g of all 18 macros, so 9.2k bus nets
  crossed the whole tile into one std area.
- The gate also flagged other findings:
  - textbook REFUSE: 120k cells, one root;
  - reset_landing FAIL: rst_n reached 32 kept rqv copies with no landing stage;
  - pins only on partial faces (N 37 %, S 33 %, E 40 %).

## Structure (RTL: rtl/hbm_next/att/ot_hnx_att4_smerge_h.sv, ot_hnx_att4_sleaf.sv)
- The merge's control never reads a data value: decode, entries, return ring, turn and publication FSM.
- The datapath is word-sliced: adder g touches only word g of the ring heads, the events and its own result.
- So the tile splits by **word half with no data crossing**. Each leaf holds:
  - 9 SRAMs (the 256-bit half of every lane/level ring);
  - 8 adders;
  - kept one-hot selects;
  - head-write muxes;
  - a 256-bit publication buffer;
  - an **identical control replica**.
- Parent `ot_hnx_att4_scl` (kind cluster, wires only) has two children:
  - `u_n` = `ot_hnx_att4_sleaf_n`: parent N face, words 0..7;
  - `u_s` = `ot_hnx_att4_sleaf_s`: parent S face, words 8..15.
- Seam (registered at both ends, straight across a 43.2 um parent band):
  - N->S, 586 bits: reset, ev, lanes 0-1 words 8..15, tags, publication request (straight from the N pin registers), plus the N publication word and fault.
  - S->N, 273 bits: lane 2 words 0..7 and lane 2 tags.
- Recurrence unchanged: ring turn 8 = ALAT 7 + head. No command crosses the seam.
- **Schedule.** Every input reaches the core 2 register stages after the parent pin in both leaves (+1 edge vs the spvm).
  Every output leaves 2 stages after the core plus the pin register (+2).
  - **COMPILER: tile outputs appear +3 edges later than the spvm's.** Publication request -> first word goes from 2 to 5 edges at the tile pins.
  - Nothing else moves: the residue a slot owns is unchanged.
- **Reset.** The pin lands in single flops (N leaf: rst_n -> r1 -> r2; S leaf: N.r1 -> g1). A kept 8-copy split stage
  (r3v / g2v, ot_rst_split, <= 32 loads per copy) then feeds the core's own kept copies. PH0 = 1 is the core residue
  reset value. Bench run m1 showed that a reset release skew between the leaves is functionally invisible: the merge is
  time-invariant at idle, so a later release relabels residues consistently.

## Benches (Verilator 5.050, ot-epyc7; tools/hbm_next/att4_scl_matrix.sh, att4_pub_bench.py --top scl)
- Same stimulus as the publication bench: 24 rounds, 576 nodes, all lanes and slots, runs of 1-4 chunks.
- The cluster's streams are checked bit for bit against the golden csum8 tree.
- Every output is checked in lockstep with the flat ot_hnx_att4_spvm 3 edges earlier: pub_v and fault every cycle, the
  data fields whenever pub_v.
- Results and witnesses: results/arch/hbm_next_1019/att4/leaf_1020/.

## Floorplan variants (gen_leaf_specs.py -> physical/ref_tile/hnx_rp3a3_sl{n,s}_{a,b})
| variant | leaf | macro rows | parent (2 leaves + 43.2 seam band) | per instance vs _nf 0.1866 mm2 |
|---|---|---|---|---|
| A (safe, primary) | 432 x 302.4 | pitch 86.4 (a band between every row), <= 4.6 live pins/um of channel | 432 x 648 = 0.280 mm2 | +50 % |
| B (compact fallback) | 432 x 216 | abutted 3-stack (as _nf), ~9.1/um channel faces | 432 x 475.2 = 0.205 mm2 | +10 % |

**DIE AREA.** At ~512 ATT columns per die, A costs about +48 mm2 per die over _nf. That would put f4c_t9p3 at ~836 + 48
= ~884 mm2 prelim, over the 858 mm2 reticle. B costs about +9.6 mm2. This decision is the owner's or DIE's. The real
area lever is the SRAM itself: 18 x 128-row macros keep 36.9 kb in 590 kb installed (6 %). A shallow 8/16-row 256-bit
macro would cut it, but it is a separate macro characterisation track.

## Parent kit (draft; needs leaf views): parent_scl_a.draft.json
Children are R0 at (0, 0) = u_s and (0, 345.6) = u_n. The parent clk is on the W face inside the seam band
[302.4, 345.6] and feeds the two leaf clk pins at x 212..220 of the seam faces. Seam pin ranges are identical on both
leaves. The gate judges each linked child pair at the child flops, TT and FF <= 80 ps.

## SAFE-DESIGN checklist (pre-gate; the census numbers come from the --cts gate's synthesis)
1. **Pins: PASS.** Every input lands in one pin register and every output is a flop. The reset lands in 2 single-flop
   stages at the face, then a kept split stage.
2. **Reach: PASS by plan.** The longest single-cycle wire is the feed-through from N pin register -> S leaf seam
   register: about 302 + 43 = 345 um < 405 (A); B is 216 + 43 = 259 um. Census to confirm.
3. **Fanout: PASS by plan.** Kept one-hot selects run per adder (fanout 32). Reset uses 8 kept copies at <= 32 loads,
   then the core's kept 16-copy vectors. Census to confirm.
4. **Depth: unchanged.** The decode and head stage are as in step 4 (landed decode, one-hot AND-OR). There is no
   combinational in->out path.
5. **Storage: PASS.** Bulk data is in SRAM (9 per leaf). The return metadata stays in the addressed ring below 2 kb.
6. **Floorplan: PASS (A).**
   - Macros are on the 43.2 lattice.
   - The full-width std bands are connected through the column channels.
   - Leaf faces stay <= 2.8 pins/um per bus range (pin_ranges + pin_balance on full faces).
   - Aspect is 1.43 (A) or 2.0 (B).
   - Fill is 34 % (A, macro-face pin bound, fill_reason recorded) or 48 % (B).
   - For B, the macro channel faces stay above 6/um. That is recorded, not waived.
7. **Clock: per leaf.** Each leaf has its own root with about 9-10k sinks over at most 432 x 302 um. The entry is at
   the seam-face centre and io_hold_margin is 0.03. Spread TT/FF <= 80 is awaited from the --cts gate.
8. **Schedule: static.** +3 edges on the publication outputs goes to the compiler (CMTP). There are no
   credits/backpressure and the II is unchanged.
