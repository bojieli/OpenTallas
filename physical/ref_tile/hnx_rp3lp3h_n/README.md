# hnx_rp3lp3h_n — north half of the SM P = 3 tile (next-release HBM die, owner 10-19 P3+(a))

**CRITICAL (hnx_rp3\*):** report only to `lanes/COORD-REVIEW-QUEUE.md` [HBM-NEXT]. Write no REVIEW.json and do not submit.

The one-piece tile `hnx_rp3lp3x` (630.72 x 2,203.2 um) has an aspect of 3.49:1 and fails SAFE-DESIGN item 6. It is now hardened as two halves, split along its lp regions. This kit is the north half. The south half is `physical/ref_tile/hnx_rp3lp3h_s`.

- **Generator:** `tools/hbm_next/sm4/hnx_rp3lp3h_kit.py`. It writes `physical/hbm_next/sm4/hnx_rp3lp3h_n_spec.json` plus the pins and stations tcl, and it also writes `results/arch/hbm_next_1019/sm4/p3/halves/{floorplan.png,geometry.json}`.
- **RTL:** top `hnx_rp3lp3h_n` in `rtl/hbm_next/sm/hnx_rp3lp3h.sv`, with one root `ck_n`.
- **Contents:** leaf 0 (xs3n plus 3 bdc plus 3 BF16 lane stacks), row 0 (`pinrow`, `row_w`, `row_e`), and the bin beat path (`pinbeat`, the `beat_t` and `beat_e` slabs, `land_n`). It also holds the N gather relays (NREL 2) and the RING of the seam gather landing (`ot_pl_land_w`, 150 b, D 4).
- **Generating the kit:** run `python3 tools/ref_tile/ref_tile.py gen physical/hbm_next/sm4/hnx_rp3lp3h_n_spec.json`. This needs the xs3n view (`physical/ref_tile/hnx_rp3lp3_xs3n/views/hnx_xs3`), which does not exist yet, so the gate is **BLOCKED** until xs3n is closed.

## Geometry
These figures come from the generator (`geometry.json`). The synthesis area will come from the gate.

| | |
|---|---|
| outline | **630.72 x 1,209.6 um = 0.7629 mm2, aspect 1.92:1** |
| hard children | 18 (13 leaf, 5 transport), 354,614 um2, hard fill 0.465; no SRAM macros |
| std-cell estimate | about 25-30k um2. This is half of the flat tile's 45-60k estimate, minus the flat lp landing and pad flops, plus the 600 ring flops. Total fill is about 0.50-0.51. |
| pins | 6,506. W: bin 2,069 + rin_n 818. E: bout + rout_n, mirrored. S (seam): sb_bank 600 + sb_vld 4. N: gin 100, xs straps 26, rst_n, ck_n. The worst 10-um window is 5.3/um (N gin, as in the flat tile). |

## SAFE-DESIGN CHECKLIST (owner 10-19)
| # | item | result |
|---|---|---|
| 1 | Pins registered; reset landed | **PASS.** bin and rin_n are captured in `pinbeat` / `pinrow`. bout and rout_n are launched by the hard `beat_e` / `row_e` cells. gin is captured by the gather registers and the xs straps by 5 stages. The seam outputs `sb_bank` / `sb_vld` are the landing ring flops, which drive the pins directly. reset_landing is ON (clock ck_n), followed by the regional run of depth 2. |
| 2 | Reach <= 405 um | **By construction; the gate verifies wire_reach.** <br>• Gather lanes in the W margin have FIRM stations at y 1190 / 886 / 586 / 286 (hops at most 304 um). The leaf-0 lane has stations at 646 / 466 / 296. <br>• The seam ring sits beside the mid stage and the sb pins (x 43-305, y 0). <br>• bin pins (y 11-507) feed the `pinbeat` capture, then `beat_t` / `land_n`. Two hops, with the capture between, each well under 405. <br>• rin_n pins (y 552-748) feed the capture, then `row0` at (432, 605). Two hops of about 220-300 um each. <br>• Lane-1 XREL stations are FIRM at (100, 762). |
| 3 | Fanout | **PASS, expected.** The `pinbeat` / `pinrow` bits are 1:1. Ring input bits fan out to 4 slots. The regional reset `lpr_n` reaches 11 child reset pins plus the ring, and every child has its own reset relay leaves. **Owed:** the native census on the mapped netlist before the first gate. |
| 4 | Depth | **PASS, expected.** The soft logic is pin registers, relay stations and the ring write decode (2-bit counter compare). No combinational in->out path exists. |
| 5 | Storage | **PASS.** The ring holds 600 b (< 2 kb). The flat lp's 2,069-b x 4 bin_l SRAM landing and the rl1_s / st_s pads are removed (see the S half). |
| 6 | Floorplan | **PASS.** All 18 child origins are on the 43.2 lattice, with halos >= 10.8 to each other and to the tile edges. Aspect is 1.92:1. There is one std-cell band, the seam band between the slabs and xs0. W / E faces carry 4.2 pins/um and the seam 2.4/um. |
| 7 | Clock | **One root, ck_n** (the region-n root of the flat lp). child_clock_ref is boundary, and io_hold_margin_ns and hold_margin_ns are both 0.03. The gate judges pin-flop spread <= 80 ps at TT and FF. |
| 8 | Schedule | **PASS, static.** Every child offset is t = 0. The seam landing adds +3 (E + 1) on the S side. The compiler record equals the `hnx_rp3lp3x_flat_lp` record: gout +3, reset +2, no new cycle. |

**Die obligations:** see `lanes/HBM-NEXT-P3.md` [HNX-SM4/SM4P].
1. The bin landing reader of the W neighbour must feed both halves' bin pins on the same edge.
2. rst_n must reach both halves on the same edge.
3. The seam N.sb_* -> S.sb_* path must be timed as a landed multicycle (-setup 2 -hold 3).
4. The slot becomes 630.72 x 2,246.4.

**Bench:** `rtl/hbm_next/sm/halves/hnx_rp3lp3x_halves_bench.sh`. The result is in `results/arch/hbm_next_1019/sm4/p3/halves/bench/`.
