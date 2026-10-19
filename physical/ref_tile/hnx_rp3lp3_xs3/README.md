# hnx_rp3lp3_xs3 — shared 3-lane x store of the SM P = 3 leaf (next-release HBM die)

Owner decision 10-19 (0le): the next-release HBM die uses P = 3 with the shared 3-lane x store (P3+(a)).
This kit hardens `hnx_xs3` (`rtl/hbm_next/sm/hnx_xs3.sv`), which `tools/hbm_next/sm4/gen_xs4.py --p 3 --name hnx_xs3` generates. It is the same mechanical copy of the closed d4g x store `ot_hbm_accel_smh_xs` as `hnx_xs4`, with P = 3 lane SRAM sets.
Spec: `physical/hbm_next/sm4/hnx_rp3lp3_xs3_spec.json`. Lane: HBM-NEXT-P3-SM, branch `claude/hbm-next-p3sm-1019`.
**CRITICAL prefix (hnx_rp3\*):** report the gate PNGs and checklist to `lanes/COORD-REVIEW-QUEUE.md` [HBM-NEXT]. Write no REVIEW.json and do not submit.

- Macros: 12 x `ot_sram_1r1w_128x256_m1_r2c2` (94.824 x 41.04), 4 per lane, lane p = row p.
- Outline: 561.6 x 289.44 um, aspect 1.94.
- Faces:
  - N: block-dot operands o_iwb + 3 x o_ixb (about 2,160 pins, 3.9/um), plus clk, rst_a and the straps.
  - S: landing inputs rl1 / bk1 / ohl1 / wl (2,903 pins, 5.2/um).
  - W: BF16 lanes 0-1 plus the kept W weight copy (787 pins, 2.7/um).
  - E: BF16 lane 2 (531 pins, 1.8/um).

## SAFE-DESIGN CHECKLIST (owner 10-19)
| # | item | result |
|---|---|---|
| 1 | Pins registered; reset landed in 2 stages | **PASS**. Kit pin_regs ON (OT_PIN_REGS=1, +1 edge in, +1 out; port_latency.json goes to the parent/compiler). reset_landing ON (OT_RST_LAND, 2 stages on rst_a); the xs4 r3 gate had failed this item. The parent's static calendar starts at least 2 edges after reset. |
| 2 | Reach <= 405 um per cycle | **PASS**. The tile is 0.56 x 0.29 mm. Every face-to-macro register hop is at most about 300 um. |
| 3 | Fanout <= ~32 in critical cones | **PASS**, with the d4g kept structure: kept per-macro pin registers per lane, the strap fan-out tree, and a kept duplicate i-stage for the W face. Check after synthesis that these are not merged (no SYNTH_KEEP_MODULES; `(* keep *)` regs). |
| 4 | Depth <= ~600 ps / 20 levels | **PASS** (expected). The datapath is the d4g xs (closed at 833 ps) with a P-wide lane mask added. The gate path classes will confirm. |
| 5 | Storage > 2 kb in SRAM | **PASS**. x slots are in 12 SRAM macros. There are no runtime-indexed flop arrays and no delay lines of 3 or more stages. ot_hdly holds hold cells only. |
| 6 | Floorplan | **Macros ON the 43.2 lattice: PASS.** Origins are 43.2 + 129.6 i and 43.2 + 86.4 j; xs4 had 16/16 off-lattice. Macros have W/E pin faces with 34.8-um channels between columns, and rows are 45.4 um apart. One std-cell band. **Fill: WAIVED, expected about 37 %.** The figure is macros 46.7k + std about 14k over 162.5k; the gate measures it. The S face carries 2,903 landing pins and needs at least 484 um at 6/um, and 4 lattice macro columns need 561.6 um. The width is therefore pin- and lattice-bound, and the height is the minimum for 3 lattice rows plus the N/S pin-flop bands. **Aspect 1.94: PASS.** |
| 7 | Clock | Single root at the N face, with a balanced tree from the xs4c2 recipe that passed: `cts_sink.sink_clustering false` + `-no_obstruction_aware`, which measured TT 61.6 / FF 61.7 ps on xs4, against 93.5 / 86.0 for the r3 one-root default. This applies the "centre-fed or regional" item to a 0.56-mm tile below the ~1-mm region threshold. Gate: pin-flop spread <= 80 at TT and FF. io_hold_margin_ns 0.03 and hold_margin_ns 0.03. |
| 8 | Static schedule | **PASS**. No credits or backpressure. The lane write mask rides the existing write stages, so the cycle timing is identical to the d4g xs. Lane-select beats are compiler-issued (CMTP isa_rows). |

## Benches (Verilator 5.050, fleet; `results/arch/hbm_next_1019/sm4/p3/bench/`)
The leaf `hnx_rp4lp4_lfx` at P = 3 instantiates `hnx_xs3`. It is checked against 3 PRODUCTION d4g leaves plus the lane-protocol model.
- PASS at P = 3, and at P = 1 / 2 (hnx_xs4 #(.P)).
- Mutants must FAIL and do: MUT1 (x-store lane alias), MUT2 (lane-select ignored), MUT3 (publish slot) and MUT4 (W-face BF16 weight sign). The witness logs are committed.

## LH-P3DIE 10-19 pin fix (re-gate)
The 08:38 --cts gate (GRT 0, pin-flop spread TT 58.6 / FF 57.1 ps, fill 38 %) placed the face pins with auto IO, which packed them into partial faces: S 2,930 pins in 297.1 of 561.6 um (9.9/um) and W 787 pins in 115.1 of 289.4 um (6.8/um). Both are above the 6 pins/um of checklist item 6.
Fix: an exact `io_tcl` (`physical/hbm_next/sm4/hnx_rp3lp3_xs3_pins.tcl`, from `tools/ref_tile/spread_face_pins.py`) spreads every face over its full length, with buses in the spec face order. N/S pins alternate M3/M5 and W/E pins are on M4. The result is N 2,176 pins at 3.9/um, S 2,903 at 5.3/um, W 787 at 2.8/um and E 531 at 1.9/um. clk sits at the N centre (x 280.7). Nothing else changed: same RTL, macros, outline and clock recipe.
Checklist after the fix: items 1-5, 7 and 8 are unchanged (PASS). Item 6 now passes for pins (every face is full and at most 6/um). The fill waiver stays: the measured fill is 38 %, and the width is set by the pins and the lattice.
