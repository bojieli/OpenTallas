# HBM-CLKLOC-1 one-page ESTIMATE (12.14b) — HBM d44f locality clock (regions + landed crossings)

2026-10-30 23:2x PDT. Plan d44f (die_plan sha a6402d40d1a2, 90 partitions, 900 ports). Analytic, **UNCHECKED** until routed.
Inputs: DIE-HBM-45 B routed street_body clock (intel2 die-hbm-45/B: tree.json + proof/tap_arrivals_TT.json), `tools/die_plan/locality.py v3`
(count_align_plan + landed_phase_ocv, unchanged), `clk_aocv_table_g021.json` (12.4a b1). Scripts: reg_stats.py, reg_est.py (this dir).

## 1. Why B fails (CHECKED on B's routed tree, regB.json / reg_est_sb63.json)
In-region routed reach (region root -> tap, detours included) is **1.0-4.6x the Manhattan reach (median 1.59)**.
SM regions reach 9-20 mm for a 5.1x3.4-mm tap box; NW_hub 14.1 mm for 8.1x4.3. Region DME balances on Manhattan
(plan stage model), the adaptive A* detour then adds 1-15 mm per leg after balancing -> routed spread 2.8 ns (T000).
Even if B were perfectly balanced, its reach alone carries 130-220 ps of OCV in 6 regions (4 SM + 2 hub): the detour is
the root cause twice (nominal skew AND OCV). Fix = balance on the physical detoured leg (`--region-dme-actual-max`, the
coherent physical DME that froze HEAD l40 (138/131 ps) and S81 g03 (138/126 ps)), not snaking on the plan model (B2 worse).

## 2. Region map (from connectivity)
locality.py v3 on d44f (v = 280 ps/mm = B routed late/path): partitions are already the connectivity units; every map
is partition-granular (bit-mm inside 0-7.9 %). Candidates: **sb63** (B's 63-region street_body map, max span 8.8 mm,
7.1 % inside), tree_s3.5c5 (66 regions, 7.9 %), part (90). Hard partitions SM 5.8x4.5 mm and hub 8.2x4.3 mm cannot be
cut without landing rings inside partition RTL, so they bound the region size. DEFAULT: keep **sb63** (no plan region
change, same as B, so C1/C2 isolate the tree fix).

## 3. Per-region tree (12.4a b1 table, same-region droop 0, core 250 ps class B both sides)
Balanced tree whose reach = 1.25 x Manhattan (street-aligned physical legs), v = 280 ps/mm, inv stages 44 ps:
| region | reach mm | insertion ps | stages | OCV clk+core ps | nominal skew budget to 150 |
|---|---|---|---|---|---|
| NW_hub / NE_hub (T028/T029) | 7.5 | 2100 | 48 | 128 | **22** |
| root (T010) | 5.7 | 1580 | 36 | 102 | 48 |
| 8 x SM (T000.. T053) | 5.4 | 1510 | 34 | 96 | 54 |
| next 51 regions | <= 5.0 | <= 1400 | <= 32 | <= 91 | 59-107 |
Verdict: 61/63 regions are feasible if the routed tree stays within 1.25x Manhattan and nominal skew <= ~50 ps
(HEAD/S81 actual-max trees reach that). **The two hubs are the risk** (22 ps nominal budget).

## 4. Landed crossings (count-aligned ring, adopted; locality v3 sb63, feed fish/fwd)
773 crossing ports, 648,265 bits; **DEPTH4 762 / DEPTH8 11 / FAIL 0**, worst margin 117.4 / 132.2 ps (gate >= 100);
feed fwd (closest to c21 link feed): D4 632 / D8 141 / FAIL 0, worst 108.2. Physical latency per crossing
{2: 178, 3: 531, 4: 60, 5: 4} cycles (fish), bit-weighted ~2.4 cycles: **+1..+4 cycles per die hop vs today's
budgeted hop = INFO (12.21)**. d44f has NO landing rows (clock.face_xing = budgeted): crossings must get CA rings in the
receiving partition glue (clock_landing_plan / bind landings) -> touches all 90 partitions' glue, no hard core.
Ring area ~3.0 mm2 at 4.66 um2/bit (LAND-HBM basis, UNMAPPED) = 0.6 % of the die.

## 5. Plan
- NOW (config-only, plan unchanged, measurement of section 3): C1 = sb63 + c21 feed + physical DME actual-max 405 on the
  HEAD freeze stack inv/ndr rep 150, snake all; C2 = B stack (inv2/1x) + actual-max 405, snake all. Both epyc2,
  kit -> clock-first GRT TT/FF -> proof -> die_sta_related (intra/seam = gate; landed class only after the CA bind).
- Then: count_align_plan on the routed arrivals -> CA bind (K/DEPTH per crossing) -> landing rows plan event (one block per
  region, G0C 0 new, strict bind) -> die_sta_related --count-align -> iterate to <= 150 / CA >= 100.
- Hub fallback if T028/T029 > 150 after C1/C2: (a) hub-only regional mesh (mesh_form, 12.8e signed mesh = common point);
  (b) related pairs from hub glue connectivity instead of all-pairs-in-partition (die_sta_related accuracy, not a
  rule change; needs ROOT-MERGE); (c) hub split with in-partition landings (RTL, owner).
