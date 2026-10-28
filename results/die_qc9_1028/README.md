# DIE-QC-9 (QC die owner): su_c zero-skew DME elongation, trial7/7b/7c, CA-OCV-1 baseline -> PARKED (OWNER 12.16e)

Runs: intel2:/srv/opentallas-scratch2/claude/die-qc9-1028 (trial7, trial7b, trial7c kits; c7*_TT/FF clock-only GRT; ca/t6 CA chain).
Plan inputs read-only from intel2 codex-die-qc-0359-1028 (K2b event qc_k2b_phase12.json, part_region.json, feed_grpP.json).
Labels: CHECKED = computed by me from the named files; UNCHECKED = model/ratio not independently checked.
Status: PARKED by COORD 12.16e (07:4x): die H-tree trial work stops; the local clock form (12.13b) is the primary path.
The in-region findings below (SU tap-leg pricing, elongation, early hang) still apply inside regions.

## 1. Estimate first (trial6 routed arrivals; scripts/est_elong.py, modelcmp.py)
- Hierarchical snake estimate (deficit to the region's grid-tap max, allotted at the highest DME node, 0.281 ps/um TT):
  ~2.0 mm per su_c region, 24 mm total (+0.45 % of the 5.38 m tree); max one leg 0.73 mm; window 30 ps: 1.6 mm/region.
  Route demand: the region is 1.64 mm2; M8+M9 at 0.08 um pitch with 40 % derate give ~25 m of track per layer there. So 2 mm x 2W2S
  (~3 tracks) is <0.03 % of one layer. Die clock usage stays 0.35 % M8 / 0.54 % M9 (GRT, CHECKED).
- The model-vs-measured check (modelcmp.py, E0) found the cause of the 153-ps-early vmr cluster. It is a MODEL bug, not
  only DME imbalance: the delay DME priced the leaf tap leg (legal driver -> core pin about 100 um inside the vmr core) as d um
  read as ps. So those pins were planned ~100 model ps late, and the tree delivered them ~150 ps TT early (CHECKED: c0/c1/c2
  are the only taps at -150..-190 in trial6 and trial7).

## 2. Tool (claude/die-qc9-1028, tools/die_plan/die_trial.py; all opt-in, defaults byte-identical, 7 new tests, 65 PASS incl test_ca_ocv)
- `--region-dme-snake REGIONS|all`: if a delay-mode merge has no zero-skew legal point, the fast kid's leg is elongated
  as a dogleg or hairpin of legal buffer sites. The leg is priced on the snapped chain (chain_ps). tree_netlist places these buffers as
  planned, and every turn is a buffer, so the router cannot shorten the snake. If a hung early tap is over-delivered, its hang leg is
  elongated. If it is under-delivered (the tree is too shallow), a new top node with an elongated leg to the old root is added.
  Under the snake opt-in, the tap leg is priced in ps (tap_wire_ps).
- `--region-dme-early-ff RATIO_FF`: the early hang target is the corner average of early_TT/1.548 and early_FF/1.293 (model ps).
- Honest note: some snakes are one-stage quanta (an added buffer with ~0 wire) when the imbalance is below one stage
  (20.8 model ps). snake_buffers are reported per region.

## 3. Builds (clock-only GRT 2W2S, 50 it; TT and FF: EXIT 0, overflow 0 on all layers, CHECKED)
| trial | change | su_c TT med/max | su_c FF med/max | su_c >150 incl OCV-est TT/FF | snakes / wire / snake bufs | cells / tree wire |
|---|---|---|---|---|---|---|
| trial6 (QC-8) | early hang | 212.9 / 225.4 | 180.4 / 194.1 | 12 / 12 | - | 29,645 / 5.381 m |
| trial7 | + snake, corner-avg early | 225.2 / 257.1 | 184.1 / 208.9 | 12 / 12 | 83 / 10.3 mm / 164 | 29,665 / 5.385 m |
| trial7b | + tap leg in ps | 65.0 / 136.5 | 52.4 / 94.5 | 1 / 0 | 27 / 5.3 mm / 61 | 29,654 / 5.391 m |
| **trial7c** | + deeper root for under-delivered early | **63.3 / 92.4** | **52.4 / 73.6** | **0 / 0** | 30 / 6.0 mm / 63 | 29,659 / 5.391 m |
- trial7 shows the elongation alone could not fix the cluster: the model was wrong, not the balance (model spread 2-3 ps).
- trial7c: model spread 2-6 ps in every su_c region. E early taps within +-5 model ps. W prog (clk_c4) is still under-delivered by
  23-28 model ps in 5 W regions: the deeper root fell back to nothing at the stage quantum. Fixed in the tool after the build
  (plain-stage fallback). That fix is UNBUILT, but the trial7c number already includes this miss.
- GRT wire 5.798 m (trial6 5.789 m). Body bays: 0 overlap / 0 macro hits / 0 unhosted (main clock_body_bays).
- Renders viewed (trial7c_plan_suc_E0/W3.png): the snakes are short, in channels or over cores on M8/M9 with buffers on legal sites. PASS-COND.
- c_* unchanged (73.5/180.7 TT, 32 TT / 12 FF regions >150): waits for the A0 centre entry (QC-A0-KITS-3).
- Residual pads to the gate on trial7c: 227/7121 taps (3.19 %), 430 pads, ALL on c_* (su_c needs 0). CHECKED (resid7c.py).

## 4. CA with CA-OCV-1 (trial6 baseline, K2b; scripts/runCA.sh: lpo -> ca_spice xing -> proof -> plan/bind with --sta-proof hull)
| plan | crossings | DEPTH4 / DEPTH8 | FAIL (no DEPTH) | worst lo / hi (bound rows) |
|---|---|---|---|---|
| with CA-OCV-1 term (table/shared, gate form) | 2537 | 2248 / 195 | **94** | 106.2 / 106.9 |
| without the term (INFO) | 2537 | 2332 / 203 | 2 | 106.2 / 127.3 |
- Failing crossings, interval width against the window (t6_fail_width.json, CHECKED arithmetic). Window = (D-1)T - 2ap - 2x100:
  DEPTH8 5423 ps, DEPTH16 12087 ps.
  - Width min/med/max is 4903/5779/8128 ps: 11 fit DEPTH8, 83 need DEPTH16.
  - The width is dominated by the START tree, not by clock OCV. The median is 6 ambiguous cycles (max 9) = ~5 ns. Clock OCV is
    p_up+p_dn median 618 ps; wander median 90 ps.
  - With OCV, only 171 of 312 start-tree edges are clean (231 without OCV): the long unshared clock (median 2.8 ns, max 7.1 ns
    on failing crossings) makes the start edges ambiguous.
  - 59 region pairs: 57 c-c, 2 su_c-c.
- So under 12.16 the fix is structural. Start edges and crossings must sit on short clock-shared links (a tree node at the
  crossing / neighbour forwarding), which bounds both the clock OCV and the ambiguous cycles. That is the local form (12.16e).
- Die STA on the INFO bind (plan-FAIL crossings dropped, never a gate number) was still running at park time:
  intel2 .../die-qc9-1028/ca/t6/sta_{none,HB4}. Collect on resume; INFO only. No --port-taps start-skew run was made (stopped by 12.16e).

## 5. Next (per COORD 12.16e)
Plan the QC local-form event from CLK-LOCAL-EST-1 (lanes/CLK-LOCAL.md, ~09:00). In-region SU/A0 trees stay local, and they keep
this lane's su_c DME + snake + tap-leg pricing. Crossings share the clock up to the crossing. Then compute DEPTH (8/16) and K
from the plan-time bound, with the same CA-OCV-1 model, and check reset release as a crossing (12.16b(iv)).
