# HBM visual-audit worklist: every OPEN finding, grouped by owner (2026-10-16 02:15 PT)
Status table: status.md. Evidence and images: findings.json, contact_sheet_*.png.
Gains are measured where stated; anything marked "est." is my estimate. The audit's estimate record so far: the T9 bank area was 4x too high, and the T3 geometry claim was refuted for q1-q3.
Each item has its own helper scope, so the helpers can run in parallel.

## H-SM (4 x P0, 1 x P2)
| # | sev | item | expected gain | dependency | helper scope |
|---|---|---|---|---|---|
| 1 | P0 | **T3 strap q0** fails TT -114.94 / FF +2.29 (strap5 2c0df5054); q1-q3 CLOSED on the same 270x270 geometry | q0 closure (+115 ps). The last missing VM strap master | none | Diff the q0 vs q2/q3 strap5 path_summary and routed odb. Find what is q0-specific: pin grant (q0 has W 1,107 vs q1 833 pins), SECDED side, write-leaf replica placement. Only if the difference is geometric, try SRAM stack to one face |
| 2 | P0 | **T1 xload_cl2_ctl**: TT -92.5, DRC 4; 345.6 um square, fill 12.3%, 10,786 pins on all faces, lane_en->bsel 24 levels across the tile | closure (+93 ps, DRC 0). Est. area: a face-sliced or strip form at ~50% fill is ~0.03 mm2 per instance (x instance count) | cl2e RTL lookahead (owner); ROOT corner-pin DRCs FIXED 4adab1ae6 (OT_PIN_CORNER_UM) | Helper A: cl2e gate + route verdict. Helper B (parallel): face-sliced variant (N/S/E/W slices, lane_en replicated per face). Measure fill and the worst path in a gate |
| 3 | P0 | **T2 xload_cl2_bdring**: clk at W centre, logic + 2,080 pins on E, W 40% empty; native L392.9 / C511.7 (cl2c) | native PASS. Est. area: width 172.8 -> ~110 um = -0.019 mm2 per instance | cl2e verdict | After cl2e: native audit. If it FAILs, a re-kit with clk on E/N and the narrower outline |
| 4 | P0 | **T6 smh_tile rp3/rp4**: W/E 3,705 pins each in 203 um (18.2 pins/um, 366 per 20 um), 17% face occupancy | removes the rp2 GRT-0116 congestion class (rp2 failed). Unblocks the SM tile = 32 die instances | rp3 verdict (running) | rp4 pin plan: spread W/E buses over >=700 um or add M6 on N/S; tr_group blocks at the windows; trial GRT in the gate |
| 5 | P2 | **T10 xload_cl2_bfq**: 345.6 x 298, 8 SRAMs, fill 33%, 1,024 pins on the W half of N | est. ~0.03 mm2 per instance from an outline shrink | cl2c verdict (READY) | Outline shrink + N-pin spread at the next re-kit |

## H-DIE (P0, P0-partial)
| # | sev | item | expected gain | dependency | helper scope |
|---|---|---|---|---|---|
| 6 | P0 | **D1 die clock**: fixed in the d3a case (0 of 24,156 cells inside outlines; hbm quad 7.9 ns, stream H-tree 13.8 ns) | a legal die case; confirmed when the d3a GRT/STA lands | d3a GRT+STA (E1, running) | Collect the d3a GRT overflow + STA classes; VIS-HBM renders and re-inspects |
| 7 | P0 | **D2 die area (v6b, 770 mm2)**: ~30 mm2 corner voids + ~23 mm2 above the HC/SFU pairs still empty | up to ~53 mm2 of placement room in a die that just grew 110 mm2 | v6b adoption | Helper: re-home HC / host slab / COLL into the corner voids; measure plan GRT + bus stages against v6b as-is |
| 8 | P1 | **T8 hdie_pc_ctrl_cfg (x128)**: H3 outline 185.76 -> 164.16 square, macros still centred; blocker TT -37.9 on ref_c -> write-ACT | closure. Area already -0.0075 mm2 per instance = -0.96 mm2 die-wide (measured outline) | H3 CTS gate (H-PCCTRL, running) | H-PCCTRL continues. Optional parallel helper: SRAMs against the E edge with clk W-mid, compared at the same 164.16 outline |

## H-NETLIST / H-HARDEN (P1, P2)
| # | sev | item | expected gain | dependency | helper scope |
|---|---|---|---|---|---|
| 9 | P1 | **T5 coll vmwrite**: clk at the N end of a 103.7 x 388.8 strip (5,123 pins) | native capture/launch at the S end; to be measured (T4's same fix gave spread 92.8 -> 37.2 ps) | v5 midclk route (running) | Collect the verdict + native audit; look at the routed density/clock PNGs |
| 10 | P2 | **T11 dbk vp4 controller**: 69x69, density mean 0.59, 27% of bins > 0.8, max 1.41 (CLOSED TT +71) | margin for the stk-strap re-kit (DRC/hold risk) | stk strap DEDUPE re-kit | Grow to ~80 um at that re-kit, keeping util < 60% |

## H-LKEP (P1 follow-up)
| # | sev | item | expected gain | dependency | helper scope |
|---|---|---|---|---|---|
| 11 | P1 | **T12 hfd_ep_static**: route 3 CLOSED TT +128.49 / FF +7.69 but native FAIL: launch 223.2 on 3 sd_tx pins (limit 220), capture 212.7 on sd_rx[1] (limit 190) | native PASS = element done (gaps of 3.2 ps launch and 22.7 ps capture) | none | Route 4 (owner, in progress): a single IDLE pin flop, clock moved west on the S face. Helper: native audit of route 4 against the sd_tx/sd_rx pins. Drop cmp1 (GRT-0116) |

## Not on the list
Not listed: refuted or no-action findings (D3, T9 reduce, R2-1, T3 q1-q3), withdrawn T7, and the routed-fixed T4 and T9 bank. Masters with no odb are listed in findings.json N1; they need a gate_layout before they can be audited.
