# DIE-S81-13 (2026-10-28): width-clean start ports (root cause + opt-in fix), S81 rebuild launched (inv2 + region DME + feed sb6)

Data: intel2:/srv/opentallas-scratch2/claude/die-s81-13. Base = DIE-S81-12 built local form (sb5 link_htree, proof/lpo on built arrivals).
Branch = claude/die-s81-12-1028 + main + claude/die-qc11-1028@40ab067d97 (die_trial --clock-cell inv/inv2, dme_feed_centroid; merged, not forked).

## (2) Width rule: where the start-port width comes from (scripts/dbg_width.py, same ctx as count_align_plan --start-tree clock)
Width limit = T/2 - 2 ap = 208.3 ps. Per-segment width on the built arrivals is about 70 ps + 0.23 x unshared ps (the 70 ps floor comes from
the corner union and the leg). Two sources, both measured on the 26 unclean ports:
* LAUNCH-side in-region insertion. Today the port launches from a LEAF tap of the parent region, and that leaf sits 747-815 ps
  (svc/lk) or 1155 ps (lk_ES0) below the fork node. The leaf -> fork segment alone is 244-335 ps wide. The retime search only tried
  capture-side nodes, so every segment kept that launch-side width and no retime could clean it.
* Single long tree edges (feed legs) of 713-1157 ps (TT, spice): lk_ES0 -> lk_ES1 (node 879 <- 763, 2.06 mm, = the ck_r879_3 large-slew
  leg), s_7S_x10 -> lk_ES0 (763 <- 762, 1.92 mm, = ck_r763_4), lk_WN0 -> lk_WN1 (2.06 mm), and phy_hbm -> svc_4/svc_6 (2.16 mm out
  of the HARD phy_hbm macro centre). One edge alone is 238-315 ps wide, and no tree node lies inside it. scripts/longleg.py: 9 edges > 550 ps.
  They are the same legs as item (4): feed ends at region-box centres over the SerDes PHY slot (2608 x 924 um of the 2886 x 1227
  lk partitions) and over the hard phy_hbm macro.
The sync flop position is the lever, not the CA depth.

FIX A (opt-in, tools): count_align_plan/bind --start-retime-up. When no capture-side node is clean, the start first climbs the
LAUNCH region's clock tree: a retime flop on the shallowest clean ancestor of the launch tap, at most up to the fork node (sync on
the spine tap). Then it descends as before. Default off, so default output is byte-identical (test). 2 new tests, plus a mutant
check (disable -> test fails). 63 + 34 related tests PASS.
Result on the DIE-S81-12 built arrivals, --start-clean width (CHECKED, own run, ca_up/): unclean 26 -> 5, crossings FAIL 4 -> 0,
start edges 917 (516 retime nodes, from 91; they are cheap flops on tree nodes), width median 185 ps. The 5 left are exactly the
long single edges above (lk_ES0, lk_ES1, lk_WN1, svc_4, phy_hbm; max path ambiguity 2). Bind fails closed on them, so this base
has no die STA row.

FIX B (plan, items 2+4): feed sb6 = sb5 with the hard phy_hbm region as a feed LEAF (svc_6 <- svc_8 and svc_4 <- svc_6, row
neighbours with 1.1k / 7.5k-bit data links). ESTIMATE plan_eval (sb5 reproduced exactly, CHECKED): D4 2277 / D8 29, 0 FAIL,
min 105.0 (sb5: 2273/33/0, 105.0). Long loops 128 -> 132 (+4 phy_hbm loops, all >= 105 at D8). The lk_* legs are fixed by
--tree-opt dme_feed_centroid=1: the feed ends at the region tap centroid in the boundary strip, off the PHY slot.

## (1)+(3)+(4) Rebuild LAUNCHED (scripts/go13.sh, ot-run unit on intel2, started 09:35)
plan_s10 + feed_sb6, die_trial link_htree --tree-site-legal --tree-site-slide, --clock-cell inv2 (QC-11 trial10: duty TT
48.2-51.3 % / FF 49.9-55.8 %, MPW 0), --region-dme delay on ALL 398 regions with early core-tap hang (--region-dme-early 1.48 /
-ff 1.28 = QC inv2 calibration, UNCHECKED for S81) + --region-dme-snake all, dme_feed_centroid=1. Then clock_body_bays overlay,
die GRT incl clock 50 it TT+FF with fall arrivals + MPW report, duty_eval, proof, lpo, CA width (--start-retime-up) + phase,
bind, die STA, and an intra-only die STA.
Item (3) root cause (DIE-S81-12 ca_phase STA): the worst intra pair is fW2_p6_b0 (col_h9 type, 6 opaque ve/vn cores). Its plain
leaf taps already spread 7587-7932 FF (342 ps, left vs right H-tree half), and the early core taps c0-c5 (core insertion 510/544
vs 250) arrive LATE, not early. link_htree ignores plan_s10's CORELAT early taps, and its legs over the opaque cores detour.
The region DME with early hang is the plan-side fix (no hold buffers).

COLLECT (job > 30 min, so it was not polled): intel2 /srv/opentallas-scratch2/claude/die-s81-13/go13.status (step lines: KIT_RC, BAYS/OVERLAY,
GRT layers, DUTY_RC -> duty13.json, plan/bind/sta width+phase -> b13_width/, b13_phase/, sta_intra.log). The kit was still running at 10:0x
(pid of die_trial kit under ot-heavy unit oth-ubuntu-3781994-*). Before any claim: view a ctree render; check slew > 320 ps legs
(longleg.py on clk/tree.json + proof) for the lk_* / phy_hbm legs; read the in-region spread on fW2/fE2_p6_b0.

## (5) F1: not progressed. It needs the col_h9 kit edit under the GEOM-44 (a)/(b)/(c) conditions (reset fanout move, TIEHI next to
its FF, re-tap x2 to clk_t11/t10 + related STA, CTS rerun). GEOM-46 CONCURRED 09:31. col_h9 DRT container 5e76e626cac4 not touched.

## go13 COLLECT (inv2 + region DME early hang on all 398 regions + feed sb6), 09:35-11:12 PDT
Code: the go13 worktree @36a56c0742 (pre-onemodel, pre-dedup). Kit 81 min (single core), GRT TT/FF 6 min, 0 overflow on every layer.
* Render data/ctree13.png VIEWED: feed (blue) 833 legs, region trees 12765 legs. The big col_h9 partitions (left and right columns)
  show region-DME stars: early core taps hang straight from upper nodes. The centre partitions keep H-trees. The bottom phy band has
  long irregular legs. 3256 tree legs are longer than 450 um (they are repeated, so they are not single wires).
* Legs over 550 ps (CHECKED, longleg.py, TT): 2. Both start at bk_sel DME node 11170: 698 ps over 686 um and 692 ps over 2016 um.
  The old ck_r879_3 / ck_r763_4 legs are gone (feed sb6 + dme_feed_centroid).
* Slew over 320 ps (CHECKED, N-line input slew): TT 204 cells (max 394.6), FF 228 (max 405.9). 197 of the TT cells are in
  region-DME trees: col_h9_r2 89, col_h9_r1 77. Each is the first repeater of a hang leg (parent leg p50 713 um, up to 1446 um),
  driven by a star node that fans out to many long legs. Tap slew max 27 ps.
* Duty / MPW (CHECKED, duty13.json): TT 46.7-52.7 %, 0 taps outside 45-55 %, MPW 0. FF 46.9-56.6 %, 94 taps outside
  (max 56.61 % at the fW2_p5_b0 clk_c4 core taps), MPW 0. MPW was checked on the combo tap ports only. MPW on the bound netlist
  (real register clock pins) is still OWED.
* CA width (legacy rule, old code, UNCHECKED under onemodel):
  - Crossings: 2306 (D4 2173 / D8 129), 4 FAIL. All 4 are s_7N_L2<->s_7S_L4 (K -19/+28, no depth); worst margin 104.3 / 112.6.
  - Start ports: 15 width-unclean, 629 retime nodes. --start-retime-max 16 gives the same 15, so this is not a retime-budget
    limit. The unclean ports sit on DME region-tree paths where each tree level costs about 420-480 ps (node arrivals
    4550 -> 4967 -> 5376 -> 5820 ...). Even with a retime on every node the width is 211-244 ps against 208.
  - Phase mode: start 0 unclean, the same 4 FAIL.
  - The old code also left 5 duplicate st: nodes on the S81-12 retime_up plan; fixed in claude/die-s81-13-rt-1028.
* Intra FF hold (CHECKED, sta_intra): -1183.9 ps (worst bk_sel clk_c3 -> clk_t2, damage 1133, CPPR 1042), TT setup -657.5.
  This is WORSE than S81-12 (-421.7). The late-only in-region spread did improve (incl. core insertion, FF):
  - p50 494 -> 220 ps, max 781 -> 636 ps (partskew.py);
  - plain taps: max 342 -> 211 ps.
  Root cause: the inv2 proof's late-early spread is 13.4 % of insertion, against 2.7 % for the BUF tree of S81-12. QC-11 t10 shows
  the same 12.8 %. The early hang lengthens the unshared path (bk_sel c3 at 192 stages vs t2 at 208, 698-ps hang leg). Taken
  together, the larger unshared path at a 5x spread outweighs the better balance. This is an inverter-model item
  (CLK-INV-CAL-1 / RM165), not a balance item.
* S81 early ratio (CHECKED, early_ratio.py; 1696 early taps; built delivered early = median plain-tap late - core tap late,
  divided by the model ps): TT p10/p50/p90 1.38 / 1.78 / 2.18, FF 1.15 / 1.53 / 1.88. QC's 1.48 / 1.28 does NOT apply as a
  single number: S81 core taps arrive early by delivered - 1.48 x model = p50 48 / p90 113 ps TT (FF 41 / 98), max 682.
  The spread (+-0.4) is per-tap leg error, so it cannot be fixed by a die-wide ratio.

## (5) F1 under GEOM-44 (a)/(b)/(c): apply ESTIMATE on joint4 (f1_apply.py, f1_pairs.py; data/f1_overlay.json)
* (a) Reset: all 19 reset buffers/inverters on the relay-FF chains were moved to their load medians, plus 1 upstream repeater.
  First hop max 56.7 um (was 512.1 with 466 FFs over 405), any hop max 242.7, 0 over 405 (CHECKED on the proposal coordinates).
* (b) Tie: 1085 TIEHI placed next to their FF, tie net <= 1.08 um. They are left unfixed so the legaliser can settle them.
* (c) Clock: the u_y_x2 group (536 FFs) re-tapped clk_t6 -> clk_t11 (483) / clk_t10 (53): FF->tap max 195 um, 0 over 220.
  - All 536 changed arcs launch from the hard core u_t4 payload: (core, clk_t6) -> (core, clk_t11 / clk_t10).
  - Built tree delta (S81-12 proof, col_h9_r1): t11 - t6 late TT -79..-2 (med -45), FF -66..+3; t10 -28..+29.
    So capture moves up to 79 ps earlier (setup -79 worst, hold better).
  - The related-pair die STA proof with the F1 placement in a kit, and the CTS rerun, are NOT done (UNCHECKED).
