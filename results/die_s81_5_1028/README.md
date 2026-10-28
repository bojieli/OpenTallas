# DIE-S81-5 (10-28 00:06-02:35 PDT): S81 region = partition clock, SerDes tap fix, GRT0 + die STA (COORD 00:06 ruling)

Code: main f1e2bcf90e (kits A/B/C/E); DIE-QC-3 claude/die-qc3b-1027@2de66bb213 (kit F).  Plan: plan_base = die-s81-3
die_plan_r98.json (06301f33d226) -> plan_s5.json (d29050658673, scripts/serdes_taps.py delta).  Data (not in git):
intel2:/srv/opentallas-scratch2/claude/die-s81-5.  CHECKED = read from my own run's log; UNCHECKED = estimate / inference.

## 1 SerDes macro vs PHY domain (ruling 1)
`scripts/serdes_recon.py` (logs/serdes_recon_{base,s5}.log, CHECKED): 12/14 phy_lk_* domains = ot_pdie_serdes macro +
63.64 um halo; the "2608x924 vs 2758x482" mismatch is two different type variants (also 1668x1163 / 1854x1163), not a
disagreement.  Two real defects: lk_ES0 domain = the whole partition; lk_ES1 domain on the die-edge side while the macro
sits on the inner side (PATH-S81 orient item, not touched).  Delta (`serdes_taps.py`): lk_ES0/lk_ES1 domain := macro +
halo; clock.keepouts_um = macro + halo per serdes type (explicit taps were rejected by taps.explicit_taps on every type:
empty / radius), serdes__t12 (lk_WS3, no macro) keepout = its domain.  Result 0/444 taps over a macro or PHY domain
(was 287/444 over domain, 244 over macro) (CHECKED).

## 2 Estimate (12.14b, ESTIMATE_v3.md, UNCHECKED)
locality v3, map part (398 regions), v 351.75 ps/mm: spine 0 FAIL (D4 2270 / D8 36), fish 0, fwd 44, top 22, spt 27.
Built: spine.  hard_phy_hbm has 1 tap under region = partition -> clock NDR option moot, not built (ruling 3).

## 3 Kit A (spine feed, leaf 200, rep 250, --tree-site-slide) - measured
* 36,185 cells, 8,329 repeaters, 6.10 m, 0 illegal; 256 unbalanced merge nodes (worst 723 um) in 99 regions, 86 > 300 um
  all SRAM/macro partitions = balance-on-legal-sites builder bug (ruling 6, DIE-QC-3) (CHECKED kit_A.log).  Kit B
  (--tree-opt full=1) worse: 4,508 unbalanced, worst 5,561 um.
* GRT0 incl clock, TT+FF, 50 it, -critical_nets_percentage 0: EXIT 0, overflow 0 every layer; M4 3.04 / M5 4.38 /
  M6 4.91 / M7 8.58 / M8 0.87 / M9 1.00 % (CHECKED logs/grt_A.log).
* Max slew: 11 legs > 320 ps: ck_r849_3 1662, ck_r778_4 1444 (feed s_7S_x10 -> lk_ES0 -> lk_ES1 past the PHY domain),
  ck_r12129_1 446, 8 at 323-370 (first repeater after a high-fanout feed branch node) (CHECKED).
* Die STA, main die_sta_related --cppr-lca (x1.00): intra TT setup +195.06 / FF hold -399.14 ps (CHECKED).
  MESO-RECONCILE --clock-cal spice (x1.0485 TT / x1.0552 FF): intra TT setup +145.81 / FF hold -448.19, skew 428 TT /
  371 FF -> FAIL vs <=150 ps (CHECKED logs/sta_A_spice.log).  Seam pairs 0 (region = partition).  Landed pairs in this
  STA are the T/2 model, not the count-aligned gate -> crossing gate = count_align_plan below.
* Count-aligned crossings on measured rows (landed_phase_ocv -> MESO-RECONCILE count_align_plan, MC 500 0 viol):
  x1.00 28 FAIL; x1.0485 17 FAIL (D4 2193 / D8 96, lo 108.8); x1.0552 17 FAIL (CHECKED logs/ca_A_*.log,
  ca_A_fails_s*.tsv).  All FAILs are nontree crossings with 3-4 ambiguous start-tree edges on the path (L width ~7.5 ns
  > D8 window): seqhost<->s_4S_L4 9, s_3S_C<->s_4S_C 4, s_4S_L3<->s_4S_x06 2, s_5S_L4<->s_5N_L2 2.
* Unshared clock per crossing (lpo_A TT, CHECKED): p50 1116 / p90 2312 / max 15904 ps.  ON-FEED crossings 2001, max
  2466 ps (0 > 3.4 ns); OFF-FEED 305, 146 ports > 3.4 ns in 38 region pairs.  The spine feed is 43 hops deep
  (~12.5 ns insertion): adjacent regions far apart on the feed tree carry ~12-16 ns unshared.

## 4 Slew legs (ruling 5): die-local driver scripts/kit_detour.py
Main tree_netlist detours a leg only if its straight run is > rep through forbidden rects; kit C applies main
legal_detour to every leg whose straight placement leaves an unrepeated span > 1.6 x rep.  Kit C did NOT fix 849/778:
main legal_detour's 5.4-um A* grid (anchored at bbox - 600 um) misses the 3-5 um legal sliver between the lk_ES0 PHY halo
and the next partition's core (scripts/probe_leg*.py, CHECKED: None at m600, path at m1500; 12129 at step 2.16).  Kit E
retries margin 1500 / step 2.16: legs detoured +13 / +14 / +164 um, worst straight span 398 um (CHECKED); GRT E overflow 0;
slew violators 11 -> 6 (330-370 ps, all fanout legs ck_r*_0, open) (CHECKED).
Die STA E (CHECKED logs/post_E.log): main x1.00 intra TT setup +234.57 / FF hold -361.75 (skew 376 / 321); spice intra TT
+183.44 / FF hold -411.15 (kit-contract -338.38), skew 394 TT / 338 FF -> FAIL (builder bug regions unchanged).  CA E
x1.00 28 / x1.0485 17 / x1.0552 17 FAIL (same nontree crossings).

## 5 Kit F (COORD 01:4x/01:5x): E on DIE-QC-3 --clock-rc 1x --region-dme delay, GRT with clock 2W2S NDR
go_grt.sh CKNDR=1: create_ndr CK2W2S (M8/M9 width 0.08, spacing 0.08 = 2x LEF) + assign_ndr -all_clocks.  The combo
GRT already keeps clock M8-M9 and signals M4-M7 disjoint, so a separate clock-first frozen pass is not built here.
Kit F clock (CHECKED kit_F/clock/tree.json): 398 region trees, 17,272 nodes, 7,252 repeaters, 3.99 m wire (A/E 6.11 m),
132 levels, worst straight span 400 um.  The kit's remaining steps, GRT F (CKNDR=1) and post F run unattended as
scripts/chain_F.sh (intel2 data dir: chain_F.log, grt_F.log, post_F.log); not read before PARK.  go_grt.sh prints the
main worktree sha in its START line; the F kit code is 2de66bb213 (kit_F.log START).

## Open / next
1. Feed depth (17 CA FAILs): relay split along the spine feed costs 4 / 11 / 43 hops per pair (+2094 port-hops) ->
   rejected; next = estimate a low-insertion trunk to spine-segment roots (no adjacent pair's LCA > ~3.4 ns up) with
   locality.py, then build.
2. 6 fanout slew legs: split the high-fanout feed branch nodes (clock repeater per child leg).
3. lk_ES1 orientation (domain on the edge side, macro inner) = PATH-S81.
