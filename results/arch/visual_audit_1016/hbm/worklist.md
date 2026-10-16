# HBM visual-audit worklist: every OPEN finding, grouped by owner (2026-10-16 10:30 PT, round 3)
Status table: status.md. Numbers and images: findings.json, contact_sheet_round3_{die,tiles}.png.
OWNER 09:46: closure first, so every item below is ranked by what blocks die GRT, die STA or native qualification.
Native numbers come from VIS-HBM running `tools/hier_contract/native_pin_audit.audit_one` on the main views (limits: launch 220, capture 190).

## H-SM
| # | sev | item | fix | gain |
|---|---|---|---|---|
| 1 | P0 | **R3-V1 VM nat2 q0/q2 native FAIL** (q0 L258.5 with 711 pins over, sp88.3; q2 L250.8 with 370 pins over). The failing pins are rr0/rr3/rr4, all in the SW corner. The clk pin is at N-centre (135, 270), about 400 um around the centred 0-um-channel stack | Give the SW-corner return flops a W-low/SW clock entry, or move the rr* pins to the N half. Add direct clk_macro entries. Open 10-um macro channels so the faces gate CTS stops reaching the SRAM clock pins | Unblocks the atomic nat2 client flip (q1 already PASSES) |
| 2 | P0 | **R3-V2 rp4c**: 3,710 of 3,759 W pins (same on E) in y 500-1000 (peak 10.4/um); M8 derated 100%; trial GRT 18/30 after 3.5 h; placement -309 ps | Re-floorplan: spread the pass-through over >= 1,000 um (tr_group rows interleaved with the XS/land blocks), or release M8. Combine this with the hard-glue/XS clock successor. Do not retry the GRT | SM tile = 32 die instances |
| 3 | P1 | **R3-V4 xcal216 r1**: native capture 254.0 on rst_n only | Reset pin flop / relay at the W face, re-kit | Native PASS |
| 4 | P0 | T1 xload ctl | ctlw r2 | - |

## H-NETLIST / H-HARDEN
| # | sev | item | fix | gain |
|---|---|---|---|---|
| 5 | P0 | **R3-V3 vmdel_lane** CLOSED TT +49.22 but native FAIL L346.6 / C274.2 / sp96.4. Failing: fill_data_i on S x 50-245 (42 pins), full/pcbad on W, rst_n. clk is at W y 40.6 | Clock entry at S-mid (x about 128), or a second entry for the E half; register rst_n | Native PASS for a die master |
| 6 | P1 | **R3-V6 F20 calendar** ww routed TT -1.82 (VT-ECO running). Logic is packed in a 44-um W block; the N strip (242 x 23 um) is empty | Only if the ECO misses: put the SRAM on the N edge so logic gets about 45 um under it, and spread the W pins over the full 117 um | Closure |

## H-SU
| # | sev | item | fix | gain |
|---|---|---|---|---|
| 7 | P1 | **R3-V5 sfucore_split**: one clk root with 18,063 flops (over 15k); rst_n has 13,745 loads | Per-region roots for the non-lane flops (clk_lane entries already exist); ot_rst_relay per region. Otherwise show a measured insertion <= 300 / spread <= 80 | Clock-rule compliance |

## H-LKEP
| # | sev | item | fix | gain |
|---|---|---|---|---|
| 8 | P1 | T12 route 4 native FAIL L259.7 / C221.3 / sp100.8 (SW corner, as the image shows) | Route 5 (in gate). If its spread still fails: the W face is free above y 172, so spread sd_tx to about 300 um and put clk at the W/S pin-field centroid | Element done |

## H-DIE
| # | sev | item | fix | gain |
|---|---|---|---|---|
| 9 | P0 | D1: d3b GRT is still running, on the **old 660 plan (grants v6)** | Collect d3b as a diagnostic only. The die evidence that counts is d4 on v5 (42/44 SYNTH) | - |
| 10 | P2 | D2 voids (4 x 7.4-10.1 mm2 beside the PHYs) | Deferred (closure-first). Use them for relay/clock-buffer homes only if the d4 GRT needs room | - |
| 11 | P1 | T8 pc_ctrl_cfg h6 NEEDS_RTL TT -50.14 (H-PCCTRL) | - | - |

## Not on the list
Fixed-routed: T2, T4, T5 (writer fsw native PASS by my audit), T9 bank. Refuted or withdrawn: D3, T3 (superseded), T7, R2-1, T9 reduce. Not auditable: HC (ETM only).
