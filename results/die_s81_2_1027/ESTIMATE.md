# S81 98-region map, COUNT-ALIGNED estimate (12.14b), DIE-S81-2, 2026-10-27

Analytic estimate before the build. All numbers UNCHECKED (own script on shared models) unless marked.
- Map: 98 connectivity regions from claude/die-s81-locality-1027@85f669cba8 (loc_spt_321.json proposed_map; groups98.json / map98.json here).
- Plan: claude/die-s81-plan-1027@7f0d18940a physical/die_plan/s81/die_plan.json.
- Script: scripts/s81_ca_estimate.py. It adds no new model, only glue between two shared tools:
  - main tools/die_plan/locality.py (d1037e4d41) supplies the crossings, the feed, the branches and the derated TT/FF intervals (landed_phase_ocv.analyse, AOCV g021 + droop regions).
  - tools/die_plan/count_align_plan.plan (MESO-COUNT-1 258bc16208) supplies the start tree, path ambiguity, K and DEPTH, with one K for TT and FF (union).
- Margins, per COORD 20:35: low = L_lo - T/2 and high = (DEPTH - 1/2)·T - L_hi, where L includes ap = T/8 = 104.1 ps. So PASS (DEPTH 4 or 8) means both margins are at least 104 ps.
- Clock wire speed v = 335 ps/mm, the MEASURED routed value (HEAD GRT-RC median), not the 176 ps/mm plan model.
- Every crossing port is a row (981 ports, 260 region pairs), loop-closing links included. Loop links are charged with the start-tree path ambiguity, so K is consistent around loops.

| feed (v=335) | D4 | D8 | FAIL | max amb cyc | worst hi | lat vs old 3 | off-feed | worst U on/off feed (ns) |
|---|---|---|---|---|---|---|---|---|
| fish (spine on max-bit spanning tree) | 895 | 62 | 24 | 3 | 130 | -388 | 192 | 4.27 / 16.3 |
| spt (H-tree regions fed from parent leaf) | 756 | 206 | 19 | 10 | 145 | +298 | 362 | 4.11 / 8.15 |
| fwd | 817 | 122 | 42 | 11 | 124 | +68 | 192 | 4.80 / 22.3 |
| spine | 623 | 319 | 39 | 9 | 133 | -80 | 192 | 4.99 / 16.9 |
| dme | 218 | 567 | 196 | 39 | 132 | -120 | 192 | 19.0 / 19.0 |
| **fishspt (spine along the shortest-path tree of the region links, fishbone regions)** | **883** | **98** | **0** | **2** | **122.6** | **-153** | 416 | **2.44 / 10.06** |
| fish + hop chains on the 24 fails | 922 | 63 | 0 | 2 | 130 | -375 | - | 24 chains, max 20 hops |
| spt + hop chains on the 19 fails | 763 | 208 | 0 | 5 | 145 | +342 | - | 19 chains, max 9 hops |

- **Verdict: the estimate PASSES directly in count-aligned mode with the fishspt feed.** All 981 crossings land in DEPTH 4 (883) or DEPTH 8 (98) with at least 104 ps on both sides. No hop chains are needed, and the total latency is 153 cycles less than the old ring's 3 per crossing.
  - The worst high-side margin (+122.6 ps) is on a DEPTH-4 row. It would move to DEPTH 8 rather than fail, so it is not binding.
- **Wire-speed sensitivity (fishspt):** at 349 ps/mm, 0 fail (793 D4 / 188 D8). At 380 ps/mm, 39 fail. The headroom is therefore about 10 % over the measured 335-349 ps/mm.
- **PHY region:** phy_hbm + eng + iqf + svc_2..12, 11.5 x 3.7 mm, insertion 2.55 ns as an H-tree. It gets its own spine along its long axis (the fishbone region tree), and the feed enters it at its centre. Render s81_ca98_fishspt_335.png (VIEWED): all crossings green, root at the die centre, PHY band bottom centre.
- **Failure mode of the other feeds.** The DEPTH-8 window (7T - 2ap = 5.6 ns) holds the derated spread. It does not hold the spread plus 2-3 whole cycles of start-tree ambiguity on off-feed links that have 13-16 ns of unshared clock. The fishspt feed keeps the off-feed unshared clock at 10 ns or less and gives only 2 ambiguity cycles.
- **Build caveat.** The shared feed tool, die_trial --tree-form spine_fishbone (LAND-HEAD-3 ec4f9b4ac2), builds the HEAD form: one vertical spine at x = clock.spine.root plus per-row ribs. That is not the link-following SPT spine estimated here. The routed build measures that tool's form as it is. If it fails, the next step is an opt-in link-following spine in die_trial (a shared-tool change via ROOT-MERGE, no fork).

## Build result (21:27 PDT), run intel2:/srv/opentallas-scratch2/claude/die-s81-2
- Plan event: fallback_regions --groups (98 map) gives 98 regions and 981 landed ports / 441,450 bits, the same as the estimate (CHECKED: reg.log). compose_plan gives types 171 -> 205, 18 ring band placement FAILs (band-room delta still needed), boot 405 cycles. die_plan_r98.json, not committed (the plan event waits for its feed).
- G0C --completeness: 14 errors = the 12 known cut-ratio errors (unchanged; the region map does not move partitions) + 2 NEW cell-cap errors from the landing rings: dsdv_slice_lepw_mus_LP__t2 403,161 and ot_s81sl_kv_leaf__t2 400,659 > 400k (CHECKED: g0_report.json diff vs die-s81/g0c/after.json).
- die_trial --tree-form spine_fishbone --rep-um 250 (LAND-HEAD-3 tool as it is) on S81 builds ONE rib at y=16.2 mm. Only one tap row touches the spine line x=16 mm, so every column hangs on 15-mm vertical stubs: 199,762 repeaters, 51.1 m of clock wire, 88 levels. Render build/sfb_clock_tree.png VIEWED. landed_topo_model: insertion up to 80.6 ns, worst -23.2 ns (UNCHECKED, model).
  - This tree form is HEAD-shaped and not applicable to S81. Die GRT was NOT launched (it would only route a known-broken tree), so no die STA either.
- Next: an opt-in die_trial tree form that follows the region links. Spine along the SPT of the region-link graph (the fishspt form estimated above), fishbone region trees, the PHY region on its own long-axis spine, 250 um repeaters. This is a shared-tool change via ROOT-MERGE with test + canary. Then GRT incl clock (50 it), landed_phase_ocv, count_align_plan, die STA.
