# DIE-QC-22 (QC die owner, successor of DIE-QC-21) -- 2026-10-28 19:3x PDT

Runs: intel2:/srv/opentallas-scratch2/claude/die-qc22-1028 (g14v gate rerun, g14w window what-ifs, kits/ot_qwen_tile_node_a0k6s).
Branch claude/die-qc22-1028 (on die-qc21@e7b32172da + origin/main 633bda658c).

## 1. 5 signed su_c views wired into the gate (--core-view), trial14 (g14 proof/bind reused, die_sta_related main)
- The g14 run matched 0 instances: the views had no provenance.json (pin match = 'view has no pins_sha256') and the gate
  plan path (die-qc18-1028/gate/ev_a0meas.json) has no cores/ dir beside it. Fix: views exported with
  tools/autopilot/export_view.py (provenance.json, pins.json) -> views/ (vmr f4kfinal 77013e5059 + routed LEC, rp1 f4g
  5ed4500430, prog s8b 6aa7f1fc4d, crh qc/closed: no LEF in the archive -> export 'incomplete' (libs+core.json+provenance
  present)); rst3 = results/cores_early_1_1028 (main); plan = die-qc20-1028/plan/ev_a0meas.json (same sha ccadb037).
  All 5 match 'canonical' (scripts/viewprobe.py). LEC record missing in the rp1/prog/crh archives (UNCHECKED here).
- Gate mode (sta_view): core_insertion view 84 / missing 780 of 864 -> FAIL closed. Missing = 720 qfd_tile_nk_a0c + 48
  qfd_tile_nl_a0c + 12 qfd_dv_s8x_btab. real_view intra pairs 3360/209284: TT setup +196.19, FF hold -100.51
  (vmr c0 -> glue t7 in sl_E4_su_c, damage 99.9); both-real 504 pairs, worst hold -24.84. UNCHECKED (NUMBER-CHECK pending).
- Declared mode: intra TT +196.19 / FF -225.0, seam TT +507.19 / FF -138.33 (= g14). Landed count-aligned PASS (TT 104.8, FF 117.7).

## 2. Shared seam_hold contract in the QC kit generator
- gen_core_kit_qc.py --seam-hold SENDER,SEAM (opt-in; KV gen_core_kit_kv form): min input SENDER-SEAM, min output -SENDER,
  sdc_lint.json hold_in_min/out_min/seam_hold_ps, freeze.json seam_hold. Default byte-identical (constraint.sdc,
  sdc_lint.json, config.mk, freeze minus rev/hash vs origin/main generator: CHECKED). 4 new tests, 16/16 PASS.
- Re-sign list (estimate from the signed ETMs, CHECKED from libs): the contract only RELAXES receiver input hold
  (0 vs -40) and asks senders for output data >= vclk_ff 202.5 + 25 + 12.5 = 240 ps FF. Signed su_c FF out_min:
  crh 310.1, rp1 260.9, vmr 264.8, prog 547.3, rst3 360.1 -> all meet it, NO re-sign needed for the 5 signed views.
  Must be (re)kitted under the contract: a0k6 node (now), a0k3 rawleaf (its -19.04 input-hold miss is inside the +40),
  a0k5 romleaf (+ its TT slew cause), btab a1713 (AP 2ce54bb5defe, legacy SDC: re-kit if it is not signed with out_min >= 240).
- a0k6 rebuilt: kits/ot_qwen_tile_node_a0k6s = recipe ot_qwen_tile_node_ilv (legacy regen is byte-identical to the
  DIE-QC-18 a0k6 kit except freeze rev/hash) + --seam-hold 25,25 + kit_modes stage (two-mode FF vclk 202.5).
  AP 7d28e91ad84d SUBMITTED 19:23 (KIT_PREFLIGHT PASS), src claude/die-qc22-1028@3a4492f246. Expect input hold -48 -> ~-8
  before repair (UNCHECKED estimate); new cost: output hold on 1027 output bits to 240 ps FF.

## 3. Glue-to-glue intra FF hold: estimate (routed arrivals only, trial14 c14 GRT)
- Damage+OCV per pair (kit contract, W=0): p50 73, p90 131, p99 161, max 225.8 (c_W2_bn_01). Routed in-region glue
  late spread: c_* med 45 / p90 75 / max 128 FF; only c_W2_bn_01 > 92.
- (i) rebalance of glue taps from routed arrivals = per-tap trims on ~all 7025 glue taps (>> the v5.1 5 % ledger) and a
  re-route that moves arrivals again (GRT residual ~34-55 ps med is not a plan feature) -> not structural, rejected.
- (ii) plan clock.tap_window W (shared gen_phys, S81 precedent 180, needs clock.seam_hold) + partition kit hold repair:
  WHAT-IF --intra-window-ps on g14 (declared, 5 views): W150 plain -38.8 (90 pairs) / OCV -75.8 (6231);
  W180 plain -8.8 (6) / OCV -45.8 (62 pairs, 42 in c_W2_bn_01); W208 (=T/4) plain +19.2 / OCV -17.8 (16, all c_W2_bn_01).
  -> (ii) is the cheaper structural form (plan keys only, kits mostly unsigned); with W=180 it leaves the c_W2_bn_01
  outlier + 20 pairs in 8 partitions (<= -20 ps OCV, UNCHECKED).
- c_W2_bn_01 outlier (scripts/outlier.py): the late t8 branch has a 1800-um in-region snake leg routed 451.8 vs model 329.4
  ps (1.37x) + 472-um leaf 126 vs 86; the early branch's 1005-um snake is 1.17x. Long single snake legs are
  under-modelled -> structural fix = split long snake legs / move the merge point (plan-computed), not a trim.

## 4. COORD spot-check (west columns vs east), ROUTED arrivals only (scripts/westeast.py, feedsnake.py; we13b/we14.json)
- trial14 glue spread TT med/p90/max: west (x 2-13.5 mm, 85 regions) 55.0/75.9/130.9 vs east (119) 46.8/82.6/109.6;
  FF med/max 48.8/127.7 vs 45.2/92.1. trial13b: west 103.3/132.0/190.6 vs east 100.0/132.4/139.6.
- Snake wire is in-region DME balancing, same share both sides (trial14 15.2 % vs 15.7 %; per 2.5-mm column 2.0-2.6 mm per
  region). Feed ladder: 0 um extra wire outside the DME regions in BOTH trials and balance_imbalance <= 2 um -> the snakes
  do not come from a west feed-length imbalance, so re-placing a feed fork does not apply. trial13b (viewed
  trial13b_plan_die.png): the >4 mm snake regions were all west (c_W3/W1 t*_10) and the west glue-row su_c snake 8.2 vs
  5.7 mm east; in trial14 (stage-cal) >4 mm snake regions are 4 west / 5 east and the glue-row west snake is 3.8 vs 5.4 mm.
  The one west excess left is c_W2_bn_01 (long snake leg under-modelled, section 3).

## 5. QC-CORES sub-task (qfd_tile_nk_a0c 720 / nl_a0c 48): BLOCKED, no build (lanes/QC-CORES.md 19:11)
- No kit/job; A0 core flat 677.7k > 400k -> needs a parent kit generator (glue ~64k + 10 romleaf + 8 rawleaf + 1 node as
  signed macros, parent trunk, composition LEC); none of the children is signed (a0k5 slew near-miss, a0k3 FF input hold,
  a0k6 = section 2). Gate mode stays FAIL closed on 768 A0 taps until then.
