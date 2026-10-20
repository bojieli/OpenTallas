# s81sl_lepnhwd -- standard NATIVE32_STD LEP (NH ot_s81sl_lep_nh) with LOCAL_WD, single std-cell band (S81-RTLFIX, 10-20, tree S81.STA.OWN.3)

Source: claude/s81-lep-localwd-1020 @74875f63b (Codex sealed d1846d61e + LOCAL_WD: per-128-bit-bank retained RX SRAM write-data
copy at the same WREG edge drives only its macro's wd_in). Evidence: results/rtl/s81_standard_lep_native32_1020/localwd_1020/README.md.
Geometry = Codex std32 draft (20 SRAMs: 2 TX columns x 5 banks on the 86.4 pitch, 2 RX rows of 5; 475.2 x 561.6), plus ONE
full-width std-cell band y 259.2..291.6 / x 2.16..473.04 (120 rows): lep_rows.tcl (end of place.tcl, before tapcell) removes
every row outside it; lep_band.tcl (PRE_GLOBAL_PLACE[_SKIP_IO] / PRE_DETAIL_PLACE) fences every movable std cell to the band
(INCLUSIVE native region; gate 053145 showed an EXCLUSIVE fence + band-only rows leaves GPL top-level all-fixed with the tie cells in it, GPL-0301) and adopts later-born cells. Codex's birth-manifest audit
layer (codex/s81-lep-physical-preflight-1020) is not used; the gate's placed-cell checks + this fence are the guarantee.

## SAFE-DESIGN checklist (owner 10-19) -- pre-gate
| # | item | result |
|---|---|---|
| 1 | pins registered, reset landing | PASS: source-registered pins (pin_regs opt-out reason in spec), rst_n lands in 2 registered stages (reset_landing.json) |
| 2 | reach <= 405 um | PASS (model): Codex row-constrained packing on this source, 0 nets > 405 (max 405.0); the gate measures it on the placed netlist |
| 3 | fanout <= 32 (kept copies) | PASS: pre-gate actual-Liberty native census 37,234 roots, max 32, 0 violations; reset included (native_*_land5.json.gz) |
| 4 | depth <= ~600 ps / 20 levels | gate-measured (textbook depth on the synthesized netlist); no new comb path (LOCAL_WD is a register copy) |
| 5 | storage > 2 kb in SRAM | PASS: TX 10 x ot_sram_1r1w_512x128, RX 10 x ot_sram_1r1w_32x128 (true SRAM; no runtime-indexed flop arrays) |
| 6 | floorplan | PASS: macros on the 43.2 lattice, 10.8 halo; ONE full-width std band (55%/50% synthesis density); W 2,234 / E 2,208 pins on 561.6 um (< 4/um); aspect 1.18 |
| 7 | clock | clk / rst_n pins on W y 272.8..288.8 = beside the band (the register mass); k-means 8 sub-trees (clock_split_km); io_hold_margin 0.03; spread <= 80 TT/FF measured by the gate |
| 8 | schedule | PASS: static; LOCAL_WD adds no edge (same WREG edge); Codex +1 outward command edge already priced (std32 MODEL.md) |

Benches (Verilator 5.050, LOCAL_WD source): see job.json; fail witnesses = localwd_1020/benches_v4 + phase_v4 (committed).
