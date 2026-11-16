# FABLE-PD-S81-F2s: r199 structural review of B6gF2s and B6gF2s1 (S81-COL-O, 2026-11-16 03:4x PST)

Plans: ev/B6gF2s.json c8a3a4936314 (sidecar 16f41153e098), ev/B6gF2s1.json beba05768bf6 (F2s + col per_type window 80).
MEASURED = my reads on epyc10. Evidence: epyc10 /srv/opentallas-scratch2/claude/fable-fix-s81-col/an/cts_f2s2_w* (STA on the r2 pilot 4_cts.odb of f2s2, placement RC, signal cap x1.45, TT, pre-repair, same script as Fable's 165/0 reads).

## Verdict
- F2s (non-col release): NONE blocking.
- F2s1 (col release): BLOCKING, three findings with numbers on col_h9_r2 (the only col type with a CTS DB).

## F2s checks (MEASURED on the plan)
| check | result |
|---|---|
| col relay form | relay/B6gF2s_event.json totals: 216 types, 402 buses, 258 lanes (228 with pin cycles), +1,008 pin cycles, 1,176 stations, 0 skipped. Col internal_stations 1,254 = F2r 1,254. Latency: 873 lanes, cycle sum 14,679 = F2r 14,679, 0 lanes changed vs F2r |
| tap_max_sinks | 3000 at type level on 216/216 col (gen_phys reads the type key first) |
| tap_group / tap_pair_affinity | absent on 216/216; reset_relay_full true on 216/216 |
| rings | ring_place ff on 1,162 bands; 82 svc bands (10 svc types) without ff, svc stays held. Col wide rings (lpad_frame_int_i0 x4, frame_int_o0 x2) are internal stations, not landing bands; f2s2 GRT 0 overflow |
| col window | flat per_type 165 on 216 (col not released on F2s; known 6,543 endpoints / -340.6 on r2) |

## F2s1 findings (col release)
1. Window 80 is not safe on r2. Same DB, same script, only the SDC window changes:

| window (grid ports / core taps) | setup endpoints | below -42 | WNS |
|---|---|---|---|
| 165 / 165 (F2s) | 6,543 | 4,928 | -340.6 |
| 80 / 80 (F2s1) | 2,835 | 341 | -255.6 |
| 80 / 20 | 325 | 118 | -199.2 |
| 40 / 10 | 165 | 14 | -185.6 |
| measured per-port (p50 10, p90 41, max 76; core taps 10) | 121 | 12 | -185.6 |
| 0 / 0 | 26 | 11 | -175.6 |

   At 80 the extra 300+ endpoints are ROM rd_out -> s<k>/q (-66..-85, 48 per ROM) and element e<k>_u_w -> bn<k>/e_r0 (-70..-88): the core taps carry the window too, and their measured window is 10. The residue at measured / 40-10 (12-14 endpoints) is only the known classes: go_tag (Spec 2/3), element sh_free/bank_free -> s ef, reset copies u_d7_6_Y (Spec 1).
   Fix: per_port_ps rows on all 216 col: grid ports (clk, clk_t*) 40, core taps (clk_c*) 10; r2 takes its measured table (s81-col-clk-impl/rows_pilot.json). Refine per type from its own first CTS with tap_window_measure. INFERENCE: other col types use the same nearest-tap / cap 3000 form, so their windows should be close to r2's; the first CTS of each confirms.
2. Three col clock rows still absent on 216/216 in F2s and F2s1: clock.tap_core_etap true, clock.tap_core_src "tree", clock.core_pin_lead_ps [{ot_rom_.*, clk, 255}]. Numbers (Spec 0, r2 CTS): without the early core sources 54 of 79 core pins miss the target by up to 190 ps (X1) vs 13 (X3); without the ROM lead the ROM rd_out -> cfg7_seq class is about 830 endpoints at -169 routed. Fix: add the three rows (keys are on main since e4b9ae9f1c1).
3. Upper taps 415..542 (CLOSURE-STRATEGY lever 3) come from main-tool core tap pricing, not from the tree. IMPL proof kit (main tools) vs f2s2 (F2r tree), same plan rows: core taps c6..c13 (element halves e10..e14 u_w/u_e, declared 465.39) arrive 520/542 vs 460/468; c0/c3 476 vs 447. core_taps.txt early_ps: main 15.39 (c6-13) and 0 (c0-5) vs F2r tree 215.39 / 184.57 / 53.17. Cause: schema.core_tap_early_ps prices an override type (450) against its own budget (COORD r104): max(0, ins - 450), so the spine shift for clk_c<k> nearly disappears and tap_balance cannot pull the pin back. Grid taps are fine (f2s2 349..479). No row reaches this (raising tap insertion_ps would misstate the core). Fix: tool change for S81-COL-CLK-IMPL: for early core taps of an override type, price early_ps against the die common latency (250), as the F2r tree did (measured on target, 460-468 for 465.39). Then a rebind-only delta (core_taps / SDC early shift change only).

## Not blocking
- go_tag, element -> s ef, reset copies: Specs 1-3, own lanes.
- svc ring_place loss: svc held.
