# DIE-QC-8 (QC die owner) — trial6 structural clock balance (COORD 06:11 ruling)

Runs: intel2:/srv/opentallas-scratch2/claude/die-qc8-1028 (kit trial6/, bays6/, clock-only GRT c6_TT/ c6_FF/).
Plan: Codex K2b event `build_inputs/event/qc_k2b_phase12.json` (sha 786407ca), regions `part_region.json`, feed `feed_grpP.json`
(all read-only from intel2 codex-die-qc-0359-1028). Tools: this branch (main 4d4c968ee0 + `--region-dme-early`).
Labels: CHECKED = computed by me from the files named; UNCHECKED = model or ratio not independently checked.

## 1. Estimate first (trial4 routed clock, pads removed) — scripts/est_*.py, estimate_regions.json
- Region spread = max - min of (tap late arrival without pads + declared core insertion), per region (CHECKED from c1_{TT,FF}).
- su_c (12 regions): 279/291 TT, 206/218 FF (median/max). Core-insertion part (prog 472.7, btab 352.8, crh 292.5 vs 250).
  With exact early taps, it drops to 89/106 TT and 74/89 FF. The rest is local-tree asymmetry.
- c_* (192 regions, 28 R4 grid taps each, A0 centre entry NOT active in K2b because `clock.core_taps` is not `early`):
  94/238 TT. This is pure local-tree spread.
  - Root cause (CHECKED, scripts/cause_c_slide.py): the planned H-tree is exactly equal length (spread 0 um).
  - The site slide moves merge points off the A0 hard cores, by up to 853 um (median of the per-region max).
  - Placed path-length spread is 333/534 um. Its correlation with arrival is 0.82.
- Measured/model leg delay ratio (leg_ps, rep 250): 1.548 TT / 1.293 FF (14,615 legs, CHECKED, scripts/calibrate_leg_ps.py).
- Estimate with early taps, and pads only as a residual to the gate (window 150 - OCV; OCV ~= 0.062 x max entry->tap,
  ratio from DIE-QC-6, UNCHECKED): 191 / 7121 taps padded (2.7 %), 224 pads. All of them are on c_*; su_c needs 0.

## 2. Trial6 built (structural forms; no pads)
- `die_trial kit ... --tree-form link_htree --tree-site-legal --tree-site-slide --rep-um 250 --leaf-um 200 --region-dme delay
  --region-dme-only <192 c_* + 12 su_c regions> --region-dme-early 1.548` (scripts/kit6.sh).
  - c_*: legal-site channel DME (DIE-QC-3/4 opt-in) replaces the slid H-tree.
  - su_c: the same DME, plus early core taps. New opt-in: each early tap hangs from the upper DME node whose subtree delay
    matches early/1.548 + its leg. This is insertion-delay balancing by construction (12.3 v5.0); no pads.
  - Every other region keeps the H-tree.
- Tree: 29,645 clock cells (trial4 46,628 base + 14,760 pads; trial5 59,774). Wire 5.38 m (trial4 7.74 m). 0 illegal.
  - Body packing (main clock_body_bays.py): 0 overlap / 0 macro hits / 0 unhosted, max move 1.92 um.
  - tree sha b9bd0aa6..., ctree.tcl 581fbf7a....
- Geometry: renders viewed (trial6_plan_full/c/suc_W3.png).
  - c_* legs run in the A0 channels.
  - su_c early taps (purple) hang from upper nodes; legs cross SU cores on M8/M9 as in trial4, with buffers only on legal sites.
  - Verdict: PASS-COND for clock-only GRT.
- Clock-only GRT, 2W2S NDR, 50-iteration budget: TT and FF both EXIT 0, overflow 0 on all layers, 29,646 nets, 5.79 m (CHECKED logs).

## 3. Measured result (trial6_spread.json, scripts/eval6.py; CHECKED arithmetic, OCV term UNCHECKED)
| class | trial4 no-pad TT med/max | trial6 TT med/max | trial6 FF med/max | regions >150 incl OCV-est TT/FF |
|---|---|---|---|---|
| c_* (192) | 94 / 238 | 73.5 / 180.7 | 61.8 / 157.1 | 32 / 12 (trial4 est: 59) |
| su_c (12) | 279 / 291 | 212.9 / 225.4 | 180.4 / 194.1 | 12 / 12 |
| sl/coll/glue/tt/native59 | <= 41 | unchanged (<= 41) | <= 34 | 0 |

Early delivery (early_delivered.txt): the target early vs the delivered early, measured against the median grid tap.
| tap | TT target | TT delivered | FF target | FF delivered |
|---|---|---|---|---|
| crh | 42.5 | 42.0 | 38.1 | 37.4 |
| btab | 102.8 | 74.8 | 92.7 | 63.3 |
| prog | 222.7 | 251.9 | 160.8 | 206.2 |

- Most of the remaining su_c spread is not the early taps. The NON-early core taps (vmr x3 + su8, target 0) arrive 153 ps
  TT early (median).
  - Cause: the DME cannot zero-skew the bottom core-pin cluster against the top grid taps without snaking.
  - The su_c DME model spread is 63-77 model ps, with 4-5 imbalanced merges per region (trial6_tree_meta.json).
- c_* got better but still has a tail. Entry->tap goes up to 1225 ps because the channel detours add 7.1 mm in total,
  which also raises OCV.
- Residual pads to the gate (trial6_residual_pads.json, scripts/resid6.py): 297 / 7121 taps (4.17 %), 634 pads, max 5 per tap.
  - su_c: 70 taps / 204 pads. c_*: 227 taps / 430 pads.
  - That is below the ~5 % sparse limit (trial5: 68.7 %, 13,146 pads), but close to it. The principle fixes below come first.

## 4. Next (structural, in order)
1. su_c DME imbalance: let a delay-mode DME merge snake when no zero-skew legal point exists (priced wire, plan-computed).
   Or enter the region at its delay centroid. This targets the 153 ps early non-early core taps.
2. btab early is under-delivered by ~28 ps and prog is over-delivered by ~29 ps: pick the hang node on corner-averaged
   targets, or take a short leg snake. Ledger anything left.
3. c_*: the A0 centre-entry plan delta (`clock.core_taps: early` with the 4 A0 core taps at 390/312 + explicit glue taps).
   This needs the glue sink census for tap radius, and A0 parent-kit CTS (QC-A0-KITS-2).
4. Then CA + die STA (spice, region key, MESO-START-2 tree-parent) and start-skew with `--port-taps` (this branch).
