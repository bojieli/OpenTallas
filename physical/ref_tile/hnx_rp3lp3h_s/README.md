# hnx_rp3lp3h_s — south half of the SM P = 3 tile (next-release HBM die, owner 10-19 P3+(a))

**CRITICAL (hnx_rp3\*):** report only to `lanes/COORD-REVIEW-QUEUE.md` [HBM-NEXT]. Write no REVIEW.json and do not submit.

This is the south half of the two-half SM P = 3 tile; see `physical/ref_tile/hnx_rp3lp3h_n/README.md` for the reason for the split.

- **Generator:** `tools/hbm_next/sm4/hnx_rp3lp3h_kit.py` produces `physical/hbm_next/sm4/hnx_rp3lp3h_s_spec.json`.
- **RTL:** top `hnx_rp3lp3h_s` in `rtl/hbm_next/sm/hnx_rp3lp3h.sv`, with one root `ck_s`.
- **Contents:**
  - leaf 1 (MX)
  - row 1
  - `land_s`, fed by this half's OWN bin pin capture `u_pbs`
  - the seam landing READ (`ot_pl_land_r`, 150 b, K 2, +3 edges)
  - the leaf-1 gather alignment ring (`hnx_pl_pad_ring`, 50 b x 3)
  - the S gather relays, NREL 2
- **Gate:** BLOCKED until the xs3n view exists.

## What the split removes from the flat lp tile
- **The 2,069-b bin_l n->s landing.** It used 4 dual-clock 16x546 SRAMs and needed a second clock in one half. This half captures bin itself and the die fans the bin landing out to both halves, so land_s runs at t = 0, as in the flat parent.
- **The rl1_s / st_s alignment pads.** These used 7 x 32x128 SRAMs plus a 26-b ring. Only the 50-b leaf-1 gather word is now aligned, by 3 edges.
- **Net effect:** 11 SRAM macros are gone, there is no second clock in either half, and the compiler offsets are unchanged.

## Geometry
| | |
|---|---|
| outline | **630.72 x 1,036.8 um = 0.6539 mm2, aspect 1.64:1** |
| hard children | 16 (13 leaf, 3 transport), 335,951 um2, hard fill 0.514; no SRAM macros |
| std-cell estimate | about 25-30k um2, including the 2,069 extra bin capture flops (about 2k um2). Total fill is about 0.55-0.56. |
| pins | 4,537. W: rin_s 818 (y 420-616, beside row1) and bin 2,069 (y 629-1026, beside land_s, 5.3/um). E: rout_s, mirroring rin_s. N (seam): sb_bank 600 + sb_vld 4, at the same x as the N half. S: gout 200 (W corner, as in the flat tile), xss 26, rst_n, ck_s. |

## SAFE-DESIGN CHECKLIST (owner 10-19)
| # | item | result |
|---|---|---|
| 1 | Pins registered; reset landed | **PASS.** bin is captured by `u_pbs` (`pinbeat`) and rin_s by `pinrow`. rout_s is launched by the hard `row_e` and gout by the gather output registers. The seam inputs pass one AND-OR 4:1 level into the `ot_pl_land_r` output flop. reset_landing is ON (clock ck_s), followed by the regional run of depth 2 and the `u_gs` run +3. |
| 2 | Reach <= 405 um | **By construction; the gate verifies wire_reach.** <br>• bin pins (y 629-1026) feed the `u_pbs` capture, then `land_s` at (43-259, 950-994). In the worst case that is two hops of at most about 290 um, with the capture placed between them (as the flat tile's 65 source regions did). <br>• rin_s feeds the capture, then `row1` at (432, 475). <br>• The seam read sits beside the sb pins (x 43-305, y 1036.8). <br>• The gather has FIRM stations at y 670 / 340 / 15 (pass lanes) and 690 / 360 / 20 (leaf-0 lane), giving hops of at most 330 um from the read. <br>• Lane-1 XREL stations are FIRM at (100, 449). |
| 3 | Fanout | **PASS, expected.** All pin captures are 1:1. Each landing read select fans out to 150 AND-OR bits through the decoded one-hot select (`ot_pl_land_r`). **Owed:** the native census before the first gate, which checks the select copies. |
| 4 | Depth | **PASS, expected.** The landing read is a 4:1 AND-OR, and the pad ring has a registered pointer. |
| 5 | Storage | **PASS.** The pad ring holds 150 b (addressed ring, not a shift chain). The flat tile's SRAM pads are removed. |
| 6 | Floorplan | **PASS.** All 16 origins are on the 43.2 lattice, with halos >= 10.8 to each other and to the edges. Aspect is 1.64:1. There is one std-cell band, the band at the seam above xs1 / land_s. |
| 7 | Clock | **One root, ck_s.** child_clock_ref is boundary, and io_hold_margin_ns and hold_margin_ns are both 0.03. |
| 8 | Schedule | **PASS, static.** u_gs is at t = 3, every other child at t = 0. gout is +3 and reset +2, identical to the `hnx_rp3lp3x_flat_lp` compiler record. |
