# H-PLANSTUDY 10-17: HBM die plan study, three organisations (no RTL)

Owner approval: HANDOFF 0dn. Branch `claude/hplanstudy-1017`. Plan level only. Every number is a model on the d4f plan graph and the run9 bus list. None of them is a die result.

**Recommendation: plan (b), d4f with per-quadrant services.**

## Method

The same tools are used for all three plans.

1. **Plan graph.** `tools/hbm_die_v15/plan_study_1017.py` writes `plan_*/compact.{P,graph,metrics}.json`. It then runs the d4f plan evaluator `v6_eval.py`, which gives:
   - the pin cut;
   - per-class bit-weighted relay stages (480 um);
   - graph bit-mm (from `hbm_globalfp.score`).

   The cut is reported with full supply over the PHY rows (the `cut_window_who.py` measure). The masked `pin_cut` shows a known PHY-row artefact: 0.66 in (b), which is really 0.08.
   - (b) and (c) use the d4f graph re-wired. SM_X, SM_OUT, KV_DESC, HBM_VM and VM_HBM go to the SM's own quadrant core, and HC_ENG goes to the quadrant HC engine.
2. **Bus model.** It covers the 1,813 run9 dry-run buses (`d4f_run9/dry_stations_r9_lanes_run8pins.json`), using driver and sink instances, bits and domain.
   - (a) is placed as run8.
   - In (b) and (c), every instance moves with its plan block.
   - Buses are re-wired by the rules R1, R2 and R3 in the tool docstring:
     - R1: a quadrant service is served by the replica in the sink's quadrant.
     - R2: die-level drivers use a tree: root, then a quadrant leaf, then local fan-out.
     - R3: COLL ring, VM ring, IDX merge and HC partials stay cross-quadrant, as class XQ.
   - Lengths are Manhattan between pins. Run9 measured / Manhattan = 1.00.
   - Stages = ceil(L / 380). Depth is calibrated on (a) by measured / model, using the median over buses at depth >= 10: forks 1.204 and p2p 1.038.
   - Relay tiles are model tiles x 1.376, which is the run9 56,308 divided by the model's 40,926 on (a).
3. **Token rate.** `tools/hgi_sim/plan_study_price_1017.py` reuses `ds_die_split`, `ds_switch_sens` and `ds_relay_latency` with the per-class stages of each plan. Base: v5carry. The same machinery reproduces the stored d4f 1,777.7 / 3,040.9 / 934.1.
4. **Network.** `tools/hgi_sim/array_net_1017.py` reuses the HBM-NET plane arithmetic (`ds_switch_planes.plane_rows`), with 32 x 100G lanes per die and TU 512 x 100G.

## Results

| | (a) d4f as is | (b) per-quadrant | (c) 8 SM / 1 stack |
|---|---|---|---|
| die outline | 22.76 x 32.17 mm = 732 mm2 | 20.20 x 31.22 = **631 mm2** | 20.20 x 16.36 = 330 mm2 |
| blocks placed | 408.9 mm2 | 411.8 | 209.1 |
| worst cut (full PHY supply) | 0.51 v / 0.70 h (README r4 flags: 0.499 / 0.521) | **0.40 / 0.47** | 0.36 / 0.42 |
| graph bit-mm | 1.20 M | **0.80 M** | 0.37 M |
| bus bit-mm (routed MST) | 2.85 M | **1.62 M** | 0.80 M |
| relay tiles | 56,308 (run9 measured) | **~37.1 k** | ~18.5 k |
| relay station-bits | 7.64 M (model; run9 8.90 M) | 4.39 M | 2.16 M |
| longest link (non-config) | 28.8 mm, 79 stages: vmb_SW0.rr4 / hb_idx__ctl.vm_rq (run9: 78) | ~17 mm, 45 stages: VM calendar fork across its own band | same 45 |
| host config fan-out (cfg_no_pad) | 127 (run9) | 66 | 64 |
| equal-age broadcast depth, model, stream / hbm / serial | 69 / 69 / 51 (run9 measured 88 / 70 / 55) | **45 / 44 / 38** | 45 / 39 / 38 |
| same, anchored to run9 (x measured / model on (a)) | 88 / 70 / 55 | **~57 / ~45 / ~41** | ~57 / ~40 / ~41 |
| cross-quadrant buses / bits | 368 / 97.9 kb (any direction) | **92 / 49.7 kb**, only on XQ fat lanes (trees) | 46 / 23.1 kb |
| clock regions (4 mm grid) | 54 grid (run8 DIE-CLOCK: hbm 25 / serial 28 / stream 36) | 48 | 30 |
| communicating region pairs: total / >1 region apart / max distance | 139 / 80 / 5 | 138 / 65 / 4 | 74 / 42 / 4 |
| neighbour skew | up to 792 ps (run8 gate) | not measured (plan) | not measured |
| replicated area vs (a) | – | about +3.7 mm2 logic (see below); die -101 mm2 | die-level blocks per die x2 in the array |
| DS AR / MTP tok/s, one tier, 377.6 ns | 1,763.0 / 3,022.3 | **1,978.4 / 3,370.7 (+12.2% / +11.5%)** | L4: 1,666.4 / 2,823.3; L2: 1,386.6 / 2,372.4 |
| DS AR / MTP, realistic (c) fabric | – | – | L4 at 428.8 ns: 1,635.7 / 2,789.6; at 480 ns (AEC): 1,606.1 / 2,756.6; 2-tier: 1,299.6 / 2,388.4 |
| Qwen3-8B AR tok/s | 933.6 (TP-8) | **955.2** (+2.3%) | 907.5 (TP-16, 1 crossing); 951.7 if in package; TP-8 on 8 SM: 532.6 |
| dies (DS array) | 192 | 192 | 384 |
| array silicon (logic dies) | 140.6 k mm2 | **121.1 k mm2** | 126.9 k mm2 |

Notes on the table:
- The price uses the plan-graph per-class stages at 480 um, the same rule as the stored d4f / v5 evaluations. The relative deltas are the result.
- The (b) gain comes from every SM-to-service class shrinking:

  | class | (a) stages | (b) stages |
  |---|---|---|
  | VM_HUB | 28.5 | 16.4 |
  | HBM_VM / VM_HBM | 32.9 | 18.9 |
  | KV_DESC | 21.4 | 8.9 |
  | SM_OUT | 21.6 | 9.0 |
  | COLL_VM | 24.1 | 14.9 |
  | COLL_EP | 15.6 | 9.6 |
  | COLL_RING | 14.4 | 9.4 |
  | SU_CORE | 14.3 | 3.7 |
  | SFU_CORE | 16.5 | 9.3 |
  | SM_X | 12.8 | 10.2 |

  SM_HBM grows from 2.9 to 4.5, because the PHY is centred under SMs spread wider.
- (b)-outer, with the cores at the SerDes edge, was also evaluated. It is worse: depth 72 / 61 / 45, COLL_RING 18 mm. Its data is kept in `plan_b_outer`.

## Network for (c) (owner requirement, first-class result)

| | (a) and (b): 192 dies | (c): 384 dies |
|---|---|---|
| one tier possible? | yes | **only with 100G single-lane ports** (512 / w >= 384, so w = 1) |
| topology | 16 planes x 200G ports; 16 TU chips; 192 of 256 ports per chip used | 32 planes x 100G ports; 32 TU chips; 384 of 512 ports used |
| cables | 3,072 two-lane | **12,288 single-lane** (4x the cables, 2x the lanes) |
| crossings per collective | 1 for a gather, 2 for an all-reduce (reduce + broadcast phases) | same |
| crossing latency | 377.6 ns (all copper, 96 packages, 2-3 racks) | 428.8 ns: + 2 x 25.6 ns RS(544,514) codeword accumulation at 100G (switch and die receiver), plus about +10 ns more small-class receiver drain (20 vs 10 ns excess) |
| packaging and reach | 2 dies per package, 2-3 racks, copper | with 2 dies per package: 192 packages, 4-6 racks, 25-50% of links > 3 m, AEC +40-80 ns, about 470-510 ns; with 4 dies per package: 96 packages, copper |
| if TU has no 100G single-lane mode | – | a 2-tier Clos at 3 x 377.6 = 1,132.8 ns |
| TOPK_MERGE at the receiver | 0.79 MB | 1.57 MB per receiver; port drain 3.97 us, hidden behind a 5.1 us delivery; 17 MB of switch buffer if unpaced |
| DS AR / MTP | (b) 1,978 / 3,371 | L4: 1,666 / 2,823 (ideal), 1,636 / 2,790 (100G copper), 1,606 / 2,757 (AEC), 1,300 / 2,388 (2-tier) |

The 512 x 100G single-lane port mode is printed for TH5; for TU it is plausible but not confirmed (HBM-NET README section 1).

## Replicated area cost of (b), per die, vs (a)

| block | change | area |
|---|---|---|
| HC engine | one 11.35 mm2 SYNTH engine split into 4 quadrant engines (slot 2.55 mm2 each), estimated at 1/4 work + 15% control | **+1.7 mm2** (slot may need to grow to about 3.3 mm2) |
| IDX scorer | two 3.05 mm clusters re-cut into 4 quarter clusters | 0 |
| IDX ctl + query | 4 local copies (0.146 mm2 each) | +0.6 |
| VM delivery lanes (ot_hbm_svc_vmdel_lane) | 16 more | +0.62 |
| XQL ctl + 2 aq_tree13 | 2 more sets | +0.12 |
| PHY-side config/status leaves (new) | 4 | +0.64 (0.4 mm squares) |
| SU scalar tree root | new | about 0.05 |
| SU RF relay chains (rfr_*) | removed | – |
| **total** | | **about +3.7 mm2 of logic** |

The die shrinks by 101 mm2 anyway. The E column (2 x 9.3 IDX + 9.5 hc_eng slot + SerDes stack) folds into the quadrants, the 2.24 mm spine and the 1.45 mm centre strip.

(c) duplicates the die-level blocks per die: the tkm 4.24 mm2 (a TP-384 TKM would need re-sizing), host, IDX coordinator, ckgen and 3 SerDes pairs. That is about +3.2 mm2 over half of (b), and the array has twice as many of them.

## Files

- `plans_abc.png`: the three plans at the same scale.
- `plan_a.png`, `plan_b.png`, `plan_c.png`.
- `plans.json`: plan and bus metrics.
- `stages.json`, `price.json`, `array_net.json`.
- `plan_*/`: compact plan + `eval.json`.

Explorer records (dataflow): `hbm_planstudy_a`, `hbm_planstudy_b`, `hbm_planstudy_c`.
