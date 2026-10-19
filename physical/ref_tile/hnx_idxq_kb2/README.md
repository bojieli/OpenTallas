# hnx_idxq_kb2: IDXQ quarter key replay buffer, pin-registered (structural redesign of hnx_idxq_kb)

Top `ot_hnx_idxn_keybuf #(NP=4, RS=1, PR=1)`. There are 17 SRAM macros (256x256). They hold the 4 PC key lines x 171 beats of one quarter scorer.

The redesign follows gate `hnx_idxq_kb` (10-19, FAIL). That gate found:
- `key_in -> key_out` was combinational over 1,202 um.
- `pbase -> tag -> key_out` was unregistered.
- Pin-flop spread was 149 / 132 ps (TT / FF).
- GRT failed with rc 137.

That was the RS=1 form. It is not squeezed here; the tile is rebuilt as follows:
- **RTL (PR=1).** Every input lands in one kept face flop. `key_out`, `fault` and `beat_out_*` leave a kept flop, so the key path is +2 edges. The scorer beat strobe and index ride the same 2 edges inside this tile.
- **Compiler.** `tools/hbm_next/hnx_idxn_calendar.py --kb-pipe 2` issues KEY/PRE 2 edges earlier. The scorer core timeline, row II 232, frame length 1315, scores, TX and done are unchanged. Only the HBM key-line delivery edge moves 2 edges earlier.
- **Composition and bench.** `ot_hnx_idxq_client_quad #(KBP=2)` uses this tile. It is checked by `KBP=2 tools/hbm_next/hnx_idxq_bench.sh OUT lockstep` with the extra compiler mutant kbp1.

## SAFE-DESIGN checklist (owner 10-19)

| # | item | result |
|---|---|---|
| 1 | pins registered, reset landed | **fixed**: PR=1 registers every in/out pin in the RTL (kept). `reset_landing` uses 2 stages (kit). |
| 2 | reach <= 405 um / cycle | **fixed**: N pin flop -> mux -> S pin flop is one stage over <= ~270 um of tile height. The old path was 1,202 um combinational. |
| 3 | fanout <= ~32 | **PASS (RS=1)**: the replay select is one kept copy per 256-bit column. The column-select copies drive ~256 mux loads each; this is guidance, local to the column. |
| 4 | depth <= 20 levels | **PASS**: one 2:1 mux + tag regen per stage. There is no in->out combinational path. |
| 5 | storage > 2 kb in SRAM | **PASS**: 17 x 64 kb macros. There are no flop arrays indexed at runtime. |
| 6 | floorplan | **fixed**: 4 abutted N-S macro stacks (pitch 41.088, no pins on N/S faces), based on the 43.2 lattice (x 43.2 / 237.6 / 432 / 626.4, y 43.2). Macro pins are on the W/E faces (10/um), with 21.6 um channels and 5.4 halos; signals use M5 over the macros (OBS M1-M4). Outline 825.12 x 272.16 is pin-bound: 4,396 key bits per face at 5.3/um. **Waived:** util 40-60% of std placeable, because this is a pass-through tile with ~4 k um2 std; total fill is ~0.55. **Waived:** aspect 3:1, set by the pin-bound faces. Std cells sit in a full-width S output band and a full-width N input strip; there are no islands. |
| 7 | clock | clk is at the S centre, next to the scorer neighbour that receives `key_out`. The pin-flop spread is measured by gate `--cts`. `io_hold_margin` is 0.03. |
| 8 | static schedule | **PASS**: no flow control. The +2 edges are priced by the compiler (`--kb-pipe 2`, II unchanged). |

## Known follow-up
`ot_hnx_idxq_qctl` checks the query-reload spacing at issue against G2MIN = 23. With KBP = 2 the compiled spacing is 25. If kb2 is adopted, the qctl kit takes `G2MIN = 25` (one constant) and must be regated.
