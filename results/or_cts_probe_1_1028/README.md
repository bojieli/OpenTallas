# OR-CTS-PROBE-1 (2026-10-28): can TritonCTS build our in-region die clock trees?

Owner question: use OpenROAD's own CTS (TritonCTS, openroad/orfs:asap7lock 26Q3-1510) for the in-region trees instead of the
die_trial region DME planner, so the unshared clock path between related registers is short? Probe only; no plan or tool change.

## Method (scripts/, data epyc2:/srv/opentallas-scratch2/claude/or-cts-probe-1)
- Region extracted from the routed die trial (scripts/extract.py): all taps of the region, region root = their lowest common tree
  node (LCA) in our tree. S81 svc_12 = go15 (intel2 die-s81-16/go15, 28 partition taps, all 756 ordered pairs related).
  QC c_W2_bn_01 = trial14, the main path (intel2 die-qc21-1028, 28 glue taps + 4 A0 core clock pins; plan ev_a0meas core
  insertion 665.8 TT / 576.5 FF vs glue 250 / 202.5 -> core pins 415.8 TT / 374.0 FF early).
- Stand-alone design (scripts/gen.py, cts.tcl): glue taps = DFFHQNx1 at the tap xy (FIRM); each A0 core = CLASS BLOCK macro at
  its real outline (OBS M1-M6) with the clock pin at the plan pin, liberty max/min_clock_tree_path = the relative insertion;
  root = M8 pin at our LCA xy, driving cell BUFx24. clock_tree_synthesis -root_buf BUFx24 -buf_list {BUFx24 BUFx16f BUFx12f}
  at TT; detailed_placement; CK2W2S NDR (same as ours); GRT clock M8-M9; estimate_parasitics -global_routing; arrivals at
  sink pins. FF re-times the TT tree. Nominal (no OCV) on both sides; spread = max-min of (arrival + declared insertion),
  which is the worst related-pair skew when all pairs are related (svc_12: 756/756).
- Ours (scripts/ours.py): same region in the routed die run, LCA cell output -> tap arrivals.

## Results (CHECKED = measured in this probe on the stated data; GRT RC, nominal)
| region | tree | spread TT / FF ps | root->tap TT ps | clock cells | max slew ps | note |
|---|---|---|---|---|---|---|
| S81 svc_12 | ours go15 (uncalibrated inv2 DME) | 215.0 / 211.4 | 632-848 | 126 CKINVDCx16 | - | CHECKED |
| S81 svc_12 | ours + stage-cal (DIE-S81-17 estimate) | 124.7 TT | - | - | - | UNCHECKED projection (go16 measures it) |
| S81 svc_12 | TritonCTS v1 defaults | 417.5 / 410.2 | 1115-1533 | 256 BUFx24, 37/path | 1138 | buffers every ~23 um, unbuffered 300-450 um leaf stubs |
| S81 svc_12 | TritonCTS v4 dist 250 + repair_clock_nets | 158.2 / 136.0 | 620-778 | 125 BUF | 239 | best; CTS 6.6 s |
| S81 svc_12 | TritonCTS v6 dist 150 + repair | 168.4 / 145.9 | 564-732 | 104 BUF | 239 | |
| QC c_W2_bn_01 | ours trial14 (stage-cal DME) | 130.9 / 127.7 | 670-800 (glue) | 182 CKINVDCx16 | - | CHECKED |
| QC c_W2_bn_01 | TritonCTS v6 dist 150 + repair | 233.0 / 180.0 | 499-732 (glue) | 139 BUF | 228 | 37 buffers INSIDE A0 cores (illegal) |
| QC c_W2_bn_01 | TritonCTS v4 dist 250 + repair | 290.1 / 223.1 | 485-775 | 137 BUF | 225 | 42 buffers inside cores |
| QC c_W2_bn_01 | TritonCTS v8 dist 250, no repair | 1430 / 1425 | 361-1791 | 57 BUF | 4463 | legal, unusable (cross-core leaf stubs) |
All 8 variants per region in runs/summary.jsonl (v2/v3 sink clustering, v5 dist 400, v7 branching distance): none beats ours on QC;
on S81 only v4/v6 beat go15, none beats the calibrated estimate. Renders: s81_v1.png, s81_v4.png, qc_v6.png (viewed).

## Findings
1. Macro insertion delay works as advertised: core pins with liberty clock_tree_path 415.8 ps got a separate macro tree and
   2-25 delay buffers; core pin arrival + insertion lands inside the glue spread (v6: 627-640 vs glue 499-732). CHECKED.
2. TritonCTS does NOT shorten the unshared path: root->tap is 0.56-0.78 ns (v4/v6) vs ours 0.63-0.85 ns, because the region
   spans 1.2 x 2.6 mm (QC) / 1.4 x 2.4 mm (S81); buffered M8/M9 delay is set by distance, not by the engine. CHECKED.
   A shorter unshared path needs smaller regions or a signed mesh (QC-MESH-PILOT-1), not another CTS engine.
3. Built for dense flop clouds: with 28 sparse sinks the H-tree leaves sit at sub-region centroids, leaving 300-450 um
   unbuffered stubs (default slew 1.1 ns S81, 3.3-4.5 ns QC); only repair_clock_nets makes it usable, and repair_clock_nets
   ignores macro obstructions and the CTS buffer list (BUFx5/6f/10/12 inside A0 cores). CHECKED (check_placement overlaps).
4. -balance_levels and -obstruction_aware print "obsolete" in 26Q3; macros are used as CTS blockages (CTS-0201) but the
   repair step is not. CHECKED (logs).
5. Buffer-only tree: high phase widened +19-29 ps (v4) / +96 ps (v1, 37 stages) at TT (fall-rise - 416.7); our inverter tree
   cancels this (CLOCK duty rule). CHECKED for BUF lists; whether CKINVDCx16 is accepted in -buf_list was NOT tested (UNCHECKED).

## What TritonCTS cannot express (and workarounds)
- Legal sites only at islands/bays (12.2): no site whitelist; workaround = placement blockages leaving only island/bay rows, and
  no repair_clock_nets (or a repair with obstruction respect) - then QC cross-core legs are unbuffered (v8) -> needs in-core
  pushdown islands, which is exactly our planner's job.
- Per-sink latency targets / planned early taps for non-macro sinks: only macro clock_tree_path liberty (works for hard-core
  pins); glue/partition taps with different declared insertion would each need a macro liberty view.
- Inverter-pair trees (duty), 405/450-um repeater rule as a hard rule, CPPR/connectivity-aware clustering, mesh, multi-source:
  not available.

## Recommendation
Keep our planner for die-level regions, recalibrated (stage-cal, DIE-S81-17 go16 / DIE-QC-21 form) - QC trial14 already
beats every TritonCTS variant (130.9 vs >=233 and illegal), and S81 TritonCTS (158) is short of the calibrated estimate (125,
UNCHECKED until go16). Use TritonCTS (a) inside partitions/cores where ORFS already runs it, with hard-core pins carrying
liberty clock_tree_path insertion, and (b) as an independent benchmark: a region where TritonCTS v4 beats the routed planner
by > 20 ps flags a planner defect (S81 go15 svc_12: 215 vs 158 did). No hybrid at die level now.
