# DIE-HBM-33 (HBM die owner, 2026-10-30 01:46-) results

Plan of record: d32q (intel1 /srv/opentallas-scratch2/claude/die-hbm-32/plan/d32q). Run dir intel1 /srv/opentallas-scratch2/claude/die-hbm-33.
Tools here are die-local drivers (no shared tool change): `tools/lane_force.py` (lane_add.py with a forced abutment chain per
pair; `LF_SNAP=1` lattice-snap station resite, `LF_PREFER=json` window target per edge, `LF_DEBUG=1`), `tools/repack_edge.py`
(re-window a block of ports on one edge at the 6 pins/um face budget, packed upward, frees the bottom of the edge),
`tools/edge2.py` (window listing per edge; gap numbers are only right on edges with ONE neighbour on that face).

## (1) V-E2: hub -> b102 row-1 feed (2746 b per half, needs Codex row1 source codex/hbm-bind-2249 0ee0ed380, not adopted)

ESTIMATE (CHECKED with G0 on each built plan): no lane-only route closes at full width on the d32q floorplan.

| var | route (per half) | base | result |
|---|---|---|---|
| ve2d | hub-b000-b010-b001-b011-b002-b012-b003-b013-b103-b102 (north column) | d33r | built 2x2746, 58 cyc; G0 FAIL 12: NE_b013 cuts 0.74-1.07, NE_b103 0.90 (> 0.6) |
| ve2f | ... b013 - io - b102 (io bypass, 1046 b) | d33r | no macro-free station chain in io (u_ep_N2); io/b102 window also split 154+269 um |
| ve2g | hub-su21-su20-b111-b103-b102 (b1 row) | d32q | no window hub/su21 (face full, 11 um free); su21/su20 edge full (max gap 18 um) |
| ve2h | b0xx row then b012 S - b111 - b103 - b102 | d33r | G0 FAIL 10 (b012 0.74, b103 0.90) |
| ve2i | ve2h + window targets (bottom of b0xx edges, b111/b103/b102 aligned 4547-5005) | d33r | G0 FAIL 2: NE_b012 @6250 0.74, NW_b111 @5000 0.84 (3274 tracks, SFU macros) |
| ve2j | hub-b000-b010-b001-su20-b111-b103-b102 | d33s | no macro-free station chain: su20 SU lane macros cover the E-face band (8 um channel) |

The b000|b010 window (brief: "widen ~14 um") is solved: d33r = d32q + 8 ports per half on that edge re-windowed at 6.0/um
(were 5.5/um), packed upward = 474 um free at 6065-6539 (need 458). d33s adds the same for b010|b001 (598 um free).
G0 PASS on d33s (ve2j = d33s, 0 lanes built). Cost: those ports move up to 220 um, so b000/b010/b001 re-kit (pins moved).
Root cause: b102 sits in the die corner; every approach crosses a 553-708 um partition vertically (b013/b012/b103/b111 cap
0.6 x 3042-3735 tracks = 1825-2241 b < 2746) or a face that is already full (hub|su21, su21|su20, NW_hub|root 65 um free).
Latency of the built forms: 58-60 cycles (UNCHECKED vs the token model; TOK to price before any adoption).
Structural options (die-owner floorplan event, NOT estimated yet): (a) move the row-1 consumer slot next to b111/b103 bottom band
or swap b102/b103 (Codex swap102 alone leaves the b013 cut); (b) home the 2746 row-1 replica FFs at b103/b111 and feed b102
over the 497 um free b103|b102 window; (c) split the feed 2 ways after an io/b013 re-layout.

## (1b) hub NE<->NW widen (2775 + 2730 b unplanned; L4/L4m 2816 b each via root are full)
Face estimate (tools/facecap.py, la/facecap_d32q.txt, CHECKED): NW_hub|root has 64.7 um free (largest 21 um) of 4320 um vs
~918 um needed for both directions at 6/um; repacking that edge to 6/um frees ~370 um (estimate, UNCHECKED) = not enough.
NE_hub|root has 2076 um free. The asymmetry is the NW-only root traffic (L156 idx return 2740 b, L74 1171, HOST_BOOT 320).
Detour hub-b112-root-b112-hub (hh1): all windows fit (hub|b112 1094 um free, b112|root 1542, root|b112 1542) but no
macro-free station chain (bad hops 406-492 um > 364 near the root end; root has 48 macros). Not closable by lane adds.

## (3) hub NW synth dhbm32s_hubnw (CHECKED from yosys stat files, rc 0, 1:05 h, 11.7 GB)
stat_legal: 726,958 cells, 288,741 FF ($_DFF_P_ 249,439, $_DFFE_PP_ 23,607, $_DFF_PN0_ 10,662, $_DFFE_PN0P_ 4,962) with hard
children as blackboxes. > 400k cells/run cap: the NW hub glue cannot be one P&R run; needs a >= 2-region split.

## (2) clock band kit k33s
ot_hgi_coll_tkm_tp192_tile_core__idpin__strap @ d32q, --clock-taps density --clock-taps-shallow, centre entry (159.84,172.8).
ot-run unit oth-ubuntu-1279727-1793350541 (intel1), goal cts, CTS 13 min, post-CTS TT setup +8.38 ps, FF hold gate PASS
(reg2reg 0 endpoints; port paths 691 at -90.54 = repaired in the FF GRT step).
TT tap mean insertion 285 ps (OT_TAP_BALANCE, target 250 +- 40, 0 delay cells) -- CHECKED from 4_1_cts.log.
FF pin-register mean 231.46 ps, 1382 samples (vclk_measured_hold.tcl ot_vmh_pinreg_mean on 4_cts.odb, FF liberty, kit RC,
placement parasitics; k33_meas.tcl in the kit dir) vs 202.5 +- 40 -> IN BAND (11 ps margin) -- CHECKED at placement RC,
UNCHECKED routed. Controls: density form 450-479 TT (out); plain CTS _k13 293 TT / 241.55 FF.
