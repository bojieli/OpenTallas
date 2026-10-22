# HBM-DIE17 10-21: exact N->O NW window decomposition (booking replay) + ONE structural proposal

Method: booking_attrib.py re-runs the unchanged relay_lanes_d4f (same argv as S4, N 017b / O 83d remote inputs) with the
capacity booking (_dec) credited to the main()-loop row and kind. Self-check: hop violations / forced / window table equal
the emitted terminal reports (N 30/205, O 27/203) and every attributed window sum equals cap.used (EXACT).

Window [10450,30800] (550 um): N 120037/97600 = 1.230 -> O 142964/92450 = 1.546.
- Kind split O: pad_forced 82537 + pad 4835 (61 %), station 55453, forced 140. N: pad_forced 68465 + pad 7479, station 44094.
- Demand +22927: hleaf_NW A-config buses +16343 (a_cfg_addr+data +11014, a_cfg_target/v/desc/launch +5329), ctl_NW_p* +4781,
  vmks_NW* +2592, xc_NW* +2132, svg_NW* -2074. Capacity -5150 (Codex 6a42 cell decomposition, confirmed).
- The pads in this window: 109 of 113 stages are hleaf_NW A-config pads for sink xc_NW2 (55 + 54).
Same pattern in the next two NW windows: [9900,30800] 117 pad stages = hleaf_NW A pads at cp_svg_NW1 (59 + 58);
[8250,30800] 105 = hleaf_NW A pads at xc_NW0 (53 + 52).

Cause: hleaf_NW = ot_hbm_host_cfg_leaf_nw (host CONFIG leaf), 268 b A-config buses, 9 sinks, sink depths 17..75.
die_relay_stations classes every multi-sink bus equal_age_pad unless CFG matches ot_hbm_host_static_ingress.(cfg_|desc_);
the host cfg leaf is not in CFG, so every near sink is padded to the 75-deep hb_coll_NW branch and nearest_cap books
the whole k-stage pad block at the sink pin (one indivisible fpp) -> forced. Die-wide equal-age pad stages: hleaf_SE 1128,
hleaf_NW 1039, host_cp_ingress 828, hleaf_NE 768, hleaf_SW 683 (hleaf total 3618).  hleaf_NW -> hb_coll_NW at 75 stages
is a ~2.6x detour of its 8.5 mm Manhattan span (separate finding).

N->O: the regression is the hleaf_NW A stations/pads that follow xc_NW2's side home into the window plus -5150 capacity;
the six-slot fix does not touch it.  r16q keeps xc_NW2 at y 31194.3 (still inside the window) -> expect NW still > 1.

ONE structural proposal (slot binding + NW cause): r16q (correct slot binding, live) + host cfg leaf config buses classed
like ingress config (cfg_no_pad: per-sink arrival recorded in the static calendar; owner rule hard-to-program is fine),
with a_launch_v alone kept equal-age on a 48-b lane, and the hleaf->hb_coll branch landed/re-routed.  Estimated effect
from this replay: [10450,30800] 142964 -> ~59k (0.64), [9900,30800] -~88k, [8250,30800] -~79k.  Needs the HC/host-cfg
receiver owner to confirm the xc/cp_svg/smw/calendar cfg receivers tolerate unequal arrival (launch aligned) BEFORE source.
