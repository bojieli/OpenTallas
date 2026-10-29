# DIE-QC-34 BTAB QC-014 V1 / V2 (COORD ruling 2026-10-29 10:09, base F3b)

Base: F3b kit intel1 `/srv/opentallas-scratch2/claude/qc-fix-2-1029/kits/qfd_dv_s8x_btab_f3b` (unit 1217062, NOT SIGNED:
TT +306.07, FF hold +7.22, pair 33.9/35.3, DRC 5, slew TT 46 / FF 24; CHECKED from its signoff.json by DIE-QC-33).

## Root cause of the 5 DRC (own probe of F3b 6_final.odb, CHECKED)
- Macro LEF `ot_sram_1r1w_128x256_m1_r2c2`: M1-M3 OBS over the full body, M4 OBS x 0.072..94.752 (pins = 24x24 nm M4 at
  x 0 / 94.8); M5 is free over the macro.
- 4 Shorts + 1 spacing are std-cell nets that run M5 over the macro, drop VIA45 **inside** the macro face and run M4 out
  across the M4 OBS: e.g. net4045 (place4047 -> _5463_, not a macro net) VIA45 at x 253.404, M4 253.404 -> 254.700, face
  of g_btb[1].u_m at 254.664 (shorts x 253.38-254.59); g_btb[3] W face x 159.91-161.03 (net10838).
- Macro PG M5/V4 stripes sit 2.0-2.1 um inside each face (252.564-252.876 and 161.844-162.156), so a 1.63-um strip
  between the pin inset (0.072) and the stripe is free of PDN.

## Slew root cause (F3b sta TT, CHECKED)
46 TT slew violators (max 419.95 ps vs 320) are BUFx3 placement buffers from the S IO band (y~7) driving single-sink
173-222 um nets to INVx1 at y 102-122 (net4012 183.6 um, net4110 222.1 um, ...): repair_design with the default wire limit
never segments them; routed RC exceeds the 40 % GRT slew margin.

## Variants (both launched 10:20 PDT in parallel, intel1, `/srv/opentallas-scratch2/claude/die-qc-34-kits/kits/`)
Common to V1 and V2 (no ECO, no new check):
- **M4 keep-off**: kit hook `sram_edge_m4_keepoff.tcl` (this dir), sourced last in `grt_pre_core.tcl` (same
  `odb::dbObstruction_create` mechanism as the existing `sram_pincol_keepoff.tcl`): M4 + V4 obstruction over the inner
  strip [face+0.072, face+1.70] of every signal-pin face (W/E) of every macro, full macro height; PDN-overlap trim built in
  (0 trims). Dry run on F3b 4_cts.odb: 16 obstructions (4 macros x 2 faces x M4/V4), CHECKED.
- **Long-net slew**: shared main `physical/common_flow/max_wire_repeat.tcl` (S81-CAPC form) as `POST_RESIZE_TCL`,
  `OT_MAX_WIRE_UM=80`. V1 log: leaf instances 15287 -> 17366, 1344 repeaters snapped off the macros (max 26.5 um), 120
  macro-crossing nets keep a strong source driver (dont_touch after PG bind).

| variant | kit | restart point | extra | unit |
|---|---|---|---|---|
| V1 | `qfd_dv_s8x_btab_f3bv1` | 3_4 resize (F3b GPL 3_3 kept) | - | `oth-ubuntu-2800166-1793294422` |
| V2 | `qfd_dv_s8x_btab_f3bv2` | 2_2 macro/halo (re-place) | E/W macro halo +1 M4/M5 track pitch (0.048 um): MACRO_PLACE_HALO 4.368 4.32, MACRO_ROWS_HALO_X 4.368, OT_MPF_HALO_UM 7.122, pin-column strip x outer edges +0.048 | try1 `oth-ubuntu-2800165-1793294422`, try2 `oth-ubuntu-2872760-1793294893`, try3 `oth-ubuntu-2915746-1793295208`: all FAILED DPL-0033 |

V2 try1 (Y halo also 4.368) FAILED at 3_5 DPL-0033: 61 plan-fixed `mp_ck_*` tree cells off-row (4.368 / 0.27 cuts a
17th row next to the macro N/S edges). The DRC class is at the E/W faces, so try2 widens only the E/W (x) halo; Y stays
4.32; try2 FAILED with 29 cells off-row, try3 (rows halo back to 4.32, only the strip x edges +0.048) the same 29.

## Results
(2026-10-29 10:4x PDT; all numbers CHECKED from the run logs unless marked)

- **V1 FAILED at GRT (no DRT)**: `[ERROR GRT-0116]` after 30 congestion iterations, final overflow 73 (M2 40, M4 25,
  M3 6, M5 2; max H 8 / V 3). F3b had 0 extra iterations. The overflow sits at the S IO band, x 150-159 / y 0-13 (48 of
  55 gcells) and x~250 / y~10, i.e. below the g_btb[1] W pin face and the macro corners: the 80-um repeat added 2,079
  cells (15,287 -> 17,366) and snapped 1,344 of them off the macros onto the halo edge, where they crowd the S band
  with the tw-data starts. Not the keep-off (all congested gcells are outside the macro bodies; the strips are inside).
  CTS/hold step before it was fine: OT_HOLD_MM after repair SS setup ws 383.78 / FF hold ws 15.00 (1,175 hold buffers).
- **V2 BLOCKED (structural, 3 tries, all DPL-0033 at 3_5, ~12 min each)**: the F3b clock plan fixes tree cells FIRM
  exactly on the pin-column strip outer edge (e.g. mp_ck_Tpp_br BUFx12f at x 119.178, mp_ck_Tqpsp BUFx10 at 261.738 =
  strip edge; probe of the failed odb, CHECKED). Any one-pitch widening of the E/W std-cell exclusion (rows halo X or the
  strip x edge) puts 29 of them off-row; Y 4.368 put 61 off-row (17th row). V2 therefore needs a tree re-plan (plan
  event, core_family_slice with halo +0.048), not a flow knob. Failed results deleted; logs in `kits/qfd_dv_s8x_btab_f3bv2/failed_try{1,2,3}/`.
- **Successor pair LIVE (same 12.17(3) two-variant rule, same keep-off, sparser repeat)**, launched 10:45 PDT, intel1:
  - V1b `qfd_dv_s8x_btab_f3bv1b` OT_MAX_WIRE_UM 120, unit `oth-ubuntu-3002592-1793295948` (client intel2 `~/dqc34k/btab_v1b.otrun.log`)
  - V1c `qfd_dv_s8x_btab_f3bv1c` OT_MAX_WIRE_UM 150, unit `oth-ubuntu-3002585-1793295948` (client `~/dqc34k/btab_v1c.otrun.log`)
  Collect: `KIT/run_route.log` (GRT-0096 table: overflow must be 0, else that variant stops), then `KIT/signoff/signoff.json`
  (TT setup, FF hold, pair skew TT/FF, DRC from 5_2_route.json, DRV slew TT/FF); finish may rc 2 on the SRAM GDS merge
  -> run signoff.py standalone with the run_kit.sh command; then routed LEC. First variant with all gates clean wins.


## DIE-QC-35 collection (2026-10-29 ~11:57 PDT; CHECKED from intel1 KIT/run_route.log + KIT/signoff/signoff.json)
- **V1b (max-wire 120, unit oth-ubuntu-3002592) FAILED at GRT** (no DRT): GRT-0116 after 30 extra iterations, overflow 55
  (M2 25, M3 14, M4 15, M5 1; max H 6 / V 4). Repeat pass 15,287 -> 16,555 leaf cells, 847 snapped off macros. Congested
  gcells: x 158.5-160.7 / y 14.8-17.7 (g_btb[1] W face S corner) and x 253.7-255.4 / y 14.8-17.7 (g_btb[1] E face S
  corner) = the V1 class, smaller.
- **V1c (max-wire 150, unit oth-ubuntu-3002585) routed, NOT SIGNED** (`v1c_signoff.json` here): GRT 0 overflow;
  repeat 15,287 -> 15,773 (286 snapped); OT_HOLD_MM GRT repair margin 15 (RSZ 519 hold bufs, GRT FF +15.00).
  PASS: TT setup +307.61 | FF hold +6.59 (measured, 0 viol) | TT pin-flop insertion 246.50-269.73 (window 230-270) |
  FF 195.20-218.39 (182.5-222.5) | related pair TT/FF 38.09/35.71 | timing_modes, PG, antenna, ft_interface PASS.
  FAIL: **DRC 6** (5_route_drc.rpt: 4 M4 Short + 2 V4 Cut Short, 2 nets: `_1154_` at (253.477-254.592, 36.72) inside
  g_btb[1].u_m E strip and `g_btb[0].m_wa[8]` at (253.477-254.592, 93.26) inside g_btb[3].u_m E strip; each = V4 at
  x 253.488 + M4 east to 254.592, shorting the keep-off obstruction AND the macro M4 OBS: the router still drops V45
  inside the E face when it has no legal exit) and **DRV slew TT 11 / FF 2** (worst u_twpd/q[343]/D 412.44,
  u_twpd/q[323]/D 353.37, _6114_/A 353.02 vs 320; F3b had 46/24). Post-route LEC not run (not clean).
- First fully clean: **neither** (V1b GRT FAIL; V1c DRC 6 + slew 11/2).
- Next ONE structural step (proposal): the keep-off obstruction is honoured by GRT only as capacity, so guides still put
  M4 inside the E-face gcells; block M4 for GRT over each macro body (+halo strip) with a global-routing region
  adjustment of 1.0 on M4 (guides then exit on M4 only outside the face), and finish the 11 slew nets with the
  post-route DRV repair on routed RC (same warm OT_ECO_FROM=grt form as PROG ffh10e), one route from V1c 4_cts. V2
  (halo widening) stays blocked until a tree re-plan (29 FIRM tree bufs off-row).
