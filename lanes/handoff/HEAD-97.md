# HEAD-97 lane handoff (HEAD die owner, successor of HEAD-96)

Started 2026-11-13 05:38 PST. Coordinator: COORD. Freeze to 11-15 04:00 (no wave switch). Visual verdict gates sign-off.
Scope: (1) NEAR-MISS ECO on routed DB (hd_turn_a 89228387ea15; hd_turn_b 90983418bc07). (2) hd_tile DRT-0255 (a4b2265f9999).
(3) hold-class hd_mesh/hd_spn_end/hd_turn_b wait on R-CLOCK (HOLD-TAP-1). (4) post-freeze adoption list (rp19p wave switch 11-15 04:00).

## State
- 2026-11-13 05:38 STATE posted.

## Paths
- epyc7 worktree /srv/opentallas-scratch2/claude/wt/head-97 (full blob-less clone, branch claude/head-97-1113 @ main 4a5e3dcf7e; train 41 pinsites NOT on main yet: merge origin/claude/head-96-pinsites-1113@38f2fe1faf before any rp20 gen)
- epyc7 work dir /srv/opentallas-scratch2/claude/head-97 (so_main = git archive of main tools + physical/common_flow; turn_a/)
- HEAD-96 plan infra (read-only use): epyc4 /srv/opentallas-scratch2/claude/head-96 (pd/rp19d.json = rp19p, pd/sidecar.json, gates.sh, remap_start.py, head_reset_exports)
- ot-run: launch from intel2 (~/.local/bin/ot-run --hosts epyc7); epyc7's own ot-run does not know epyc7.

## Posted (all on origin)
- 05:38 STATE; ~06:00 RESULT DIEVIEW-F1 hold on hd_tile in kit_wave.json (backup autopilot/kit_wave.json.bak-head97-dieviewf1-*); 06:00 STATE took F1/F2; adoption list PLAN line.

## (1) hd_turn_a near miss 89228387ea15
- Autopilot ECO i1 (epyc8 .../hd_turn_a/attempt_3/gen/hd_turn_a/eco_20261113_122551_1562311/i1): TT +103.96, FF +6.26, DRC 0, 112 TT / 108 FF slew pins on 110 nets.
- Cause: BUFx16f "wire" buffers inserted by ECO repair_design on PLACEMENT RC drive single INVx1 ring dsel loads 175 um away, routed on M2/M3 only -> 450 ps slew.
- ECO2 running: epyc7 head-97/turn_a/eco2 (seed copy of i1 = turn_a/seed_i1), eco_loop main tools, OT_SLEW_MARGIN=50 OT_PRD_MAX_WIRE_LENGTH=120, --owner-override --lec. ot-run log intel2 /srv/opentallas-scratch2/claude/head-97/turn_a_eco2.otrun.log. Record turn_a/eco2/eco_loop.json.
- Note: rp19p changes hd_turn_a (write_chunk 16) -> an rp18 sign-off is superseded at the 11-15 switch; still worth it as a real view and ECO proof.
- hd_turn_b 90983418bc07 not local (R-CLOCK cross-tap class) -> no ECO.

## (2) hd_tile (DIEVIEW F1) - held, analysis so far (not built)
- DRT-0255 net u_core.u_xo/net34825: 2-pin BUFx16f hop from W of elemB to the 13.3-um band above elemB (elemB 216-501 x 734-1019.15; core top 1032.48). OBS M1-M5 on elemB.
- u_xo (the W->E i/o 565-bit pass, face windows y 708-1008 straight across elemB) = 2,751 cells: 334 repeaters in the N band, 218 in the 34.5-um A/B street, 815 W/E lobe buffers; 139 nets have guides over elemB. ft max wire 110 < elemB 285 um.
- Relay "column" x 338.9 = relay_sites of u_b.g_a[*].g_ais (2596 sites total, ~1220 A-input relays) sited AT elemA core pins facing the N-S street; moving them into the E-W street detaches them from their pins (pin_reg). Options: rotate/mirror A cores so the 245-pin faces point at the E-W street / outline (cores may move/rotate), or widen the street +17.28 (die event). Needs core pin face check (core_pins/elemA_pins.json).
- Taps clk_t10..t13 etc. are die islands (clock.die_islands_um, 44 ports, tap_max_sinks 1500; clk_t13 2077 over cap). Tap split = die clock island change -> needs the die clock run (DIEVIEW F3, unowned) for windows.
- Hold build added 21,273 hold cells (29%) on 117-ps windows.
## (3) hold types: wait R-CLOCK merge (HOLD-TAP-1 branch claude/hold-tap-1-1113).
## (4) adoption list posted (PLAN line). Plan diff rp18r2->rp19p: 6 types changed (turn_a, turn_b, st_n4, spn_wshim_rx, spn_end, spn_eshim_rx).

## NEXT (rp20 event on rp19p, one event, then private place/route hd_tile + hd_spn_end, READY)
- F1a tap_pair_affinity + split overloaded hd_tile islands (clk_t13/t16/t22) + windows from die clock run.
- F1b relay/landing out of the N-S street (see note above: core orientation or street width, decide on pin data).
- F1c reach_homes W/E lobes + reach_rules.py fix --rules 2; ALSO re-home the u_xo pass (station on the A-row E-W street or declared over-macro hop).
- F2 hd_spn_end one tap per station row (68 -> ~25-30), tap_pair_affinity hd_spn_end + hd_mesh; delete orphan taps hd_turn_b (clk 13 sinks @92,232; clk_t1 3 @92,17), hd_spn_eshim_rx (clk_t2 5, clk 19, clk_t1 15). Coordinate HOLD-TAP-1.

## F1b geometry facts (06:3x)
- elemA pins (core_pins/elemA_pins.json, R0): E 244, S 130, W 81, N 1, interior 10. Orients: eA0 MX, eA1 R180, eA2 R0, eA3 MY -> all four 244-pin E faces point into the N-S street (245 vs 245 per street_rule), 81-pin faces to the W/E outline.
- Horizontal budget per A row: 708.48 - 2 x 319.68 = 69.12 um (bottom row W 17.28 / street 25.92 / E 25.92; top row 17.28 / 34.56 / 17.28). street_rule rp19d hd_tile: N-S street 25.92 and 34.56 need 43.2; outline faces 17.28/25.92 with 81 pins need 43.2; elemB N outline_sliver 17.28.
- 90-degree rotation of the signed cores is not an option (layer directions); only R0/R180/MX/MY. So zero growth cannot meet street 43.2 + two outline streets (129.6 > 69.12). Choices: (i) street 43.2 + outlines 12.96/12.96 (81 pins each; seam partner gives the other half if outline streets are judged across the abutted seam, CHECK with RULES-STREET-1), (ii) +17.28 tile width (die event, pre-approved class), (iii) relays only out of the street (DIEVIEW zero-growth): but the street relays ARE pin relays of the 244-pin faces (u_b.g_a[*].g_ais relay_sites, ~1220), pin_reg would break.
- Tap/island edits (F1a split, F2 orphan/merge) are clock.die_islands_um entries = die clock contract: need the die clock tool run (DIEVIEW F3, unowned) to re-derive islands + windows consistently. Ask COORD to give F3 to HEAD-97 or a clock lane before rp20.
