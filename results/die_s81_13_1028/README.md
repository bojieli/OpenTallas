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
