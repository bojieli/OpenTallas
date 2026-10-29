# DIE-S81-16 (2026-10-28) S81 die owner

## 1. dme_region_tree merge-mode join(): cause + fix (shared tool, READY ROOT-MERGE)
Tool branch `claude/die-s81-16-join2-1028@4d10067fe9` (= a041fd7ad6 join budget + 4d10067fe9 SiteMap.in_part index), base d04bc5ca95.

Cause (CHECKED, small reproducer, FakeSite 1500 um, random taps): `join(join(a,k),o)` can descend again into the node it
has just built, so calls double per level up to the depth cap of 24. Max depth reaches 25 even with early=0 at n>=32;
n=128 takes 22057 calls / 25.7 s. Merge mode (early core taps as sink delay) gives 3-10k calls on n=16-64.

Fix:
- `DME_JOIN_BUDGET=4096` calls per top-level join. Over budget: drop the partial nodes, then run a bounded monotone
  join-down (never re-enters built nodes). Where the fast side cannot reach, merge with a snake (detour) leg on the fast
  side, which is standard DME delay balancing. Logged in stats as join_fallbacks / worst_gap_ps / worst_imb; these keys
  are absent when under budget.
- SiteMap.in_part: a bucket index of the partition rects, same boolean as the linear scan. The scan was ~70 % of
  merge-mode runtime (profile of region call_097).
- Tests: tools/die_plan/test_die_trial_dme_join_budget.py (6 tests); all test_die_trial*.py pass, 79 passed (docker py3.12).

Replay of the real go14 inputs (all 398 dme_region_tree calls dumped from the go14 kit = plan_s10 + map398 + merge flags;
scripts dump_dme.py / replay_one.py / replay_all.py / replay_summary.py / jc_one.py; data
intel2:/srv/opentallas-scratch2/claude/die-s81-16/{dump,replay.jsonl,replay_new2.jsonl,jc.jsonl}). All CHECKED:
- hang mode (go13-class): 389/389 regions byte-identical, old tool vs new tool, full output hash.
- merge mode (go14 input): 278/278 regions where the old tool finished in <120 s are byte-identical. 110 regions time out
  on the old tool at 120 s. The new tool finishes all regions (max 553 s), with 1 fallback (gap 142 ps, imbalance 0 after).
- Join calls per top-level join, budget off: hang max 3046 (p99 3046, 398 regions); merge max 2806 (50 sampled regions).
  So 4096 is a pure runaway guard on these inputs. Budget 512 / 128 cuts merge time 1.2x / 2.5x but adds 80 / 115 fallbacks.
- in_part index: 98+98 regions byte-identical to the budget-only tool, 1.95x faster in hang mode and 1.85x in merge mode.
- Merge-mode kit DME, serial: sum 34686 s on the budget-only tool, about 5.2 h with the in_part index (UNCHECKED
  extrapolation). Merge mode is inherently slow: every join runs merge_point_delay plus a snake search.

## 2. go14
At 14:45 there was no KIT_RC, so the brief applied. Pid 1812622 (die_trial kit plan_s10 ... --out go14/kit; args checked)
was killed after 2 h 53 min of join recursion. The partial kit (256 MB) was deleted, and this is noted in go14.status.

## 3. plan_s11 (ESTIMATE before build)
plan_s11.json sha 778e9af860b0 = plan_s10 (5f014a8d3554), scripts/plan_event_s11.py, then delta_signed_view_pins_1028.py:
- (a) bf_col clk pin fix @990771bcbb merged (15db468816).
- (b) rom_elem_q 108 cores bound to the `_gb` master (module, lef, pins).
- (c) rom/bf_col type-tap insertion set to 285 TT. This is the midpoint of the measured 250-320 ps and is UNCHECKED;
  FF = TT x the plan_s10 ratio. Tap xy not moved: taps stay at the CORELAT boundary point.
- (d) delta pins: rstg/payload536 FOLLOWS-VIEW (abstract repointed); NNfu/cfg7 SAME; vq KIT-STALE (830 vs 702 pins).

Estimate (scripts/est_s11.py, CHECKED arithmetic on plan values): early instance taps 1696. Taps with sink delay <50
model ps: 171 -> 1491. rom_elem_q (864): early 260 -> 35 TT. bf_col (456): early 294 -> 35 TT.

## 4. Per-region intra hold (scripts/per_region_hold.py, uses main die_sta_related.time_class)
On the go13 cp13 proof (plan_s10, declared insertion), CHECKED: it reproduces the die worst values, TT setup -106.97 and
FF hold -724.05. Hold is negative in 397/397 regions. FF worst regions: bk_sel -724.05, svc_12 -306.6, svc_13 -299.7,
svc_8 -274.9, fE1_p6_b2 -273.4, svc_9 -269.4 (prh13/per_region.json).

## 5. go15 (one build)
intel2:/srv/opentallas-scratch2/claude/die-s81-16/go15, `go15.sh` via ot-run, started 15:08:24 PDT, code 237ec828fd,
plan 778e9af860b0. Options: merge mode + --cell-paths (the first attempt on b45d4f20cc was killed by me at 15:04;
its logs are in attempt1/).
"Branched slew legs": die_trial has no such option. Merge mode removes the hang stars that carried the go13 slew cells.
go15 reports legs >450 um and slew cells.
Collect from go15.status: KIT_RC, JOIN_FALLBACKS, GRT TT/FF, DUTY (both edges/MPW), slew, legs>450 (go13: 3256),
PER-REGION (per_region.json), sta_view, RENDER ctree15.png (view it), CA width/phase with OCV.

## 6. vq
Not started. vq is KIT-STALE (signed y[255:0] 830 pins vs plan 702). It needs a re-kit from ot_s81sl_vq_tpl.json on main
RTL through tools/autopilot/enqueue.py.

## 7. FF hold cause classification on go13 (COORD 15:2x, ESTIMATE, nothing fixed per 12.16)
Script: scripts/hold_classify.py. It runs main die_sta_related.py unchanged with the go13 cp13 proof, plan_s10, the same
STA flags and --core-insertion declared, and reproduces FF intra -724.05 with 171391/178894 pairs negative. It recomputes
each pair's min-hold endpoint combo:
`hold = data_min - unc_h - ocv_h - (tree skew ec-ea + endpoint latency skew) - uncredited spread (lc-ec-cppr credit)`.
Output: hold13/classify_go13_FF_worst200.json.

| term (ps, mean) | worst 200 (mean h -363.7) | all 171391 negative (mean h -77.5) |
|---|---|---|
| data_min = clkq_min - hold (declared zero-logic register) | +25.5 | +25.5 |
| unc_h | -25.0 | -25.0 |
| AOCV + shared droop (clock-ocv table) | -46.7 | -29.0 |
| tree skew, early-early (ec - ea) | -307.9 | -6.6 |
| declared core insertion offset (latB - latA) | +106.6 | +2.9 |
| uncredited late/early spread below the LCA | -116.2 | -45.3 |

- Dominant term: worst 200 = clock skew 117 / uncredited spread 83. All negative pairs = uncredited spread 127250 /
  unc 19998 / skew 16427 / ocv 7716.
- Model floor: zero data delay gives 25.5 - 25 = +0.5 ps margin, so any spread or OCV term > 0.5 ps fails. That is why
  397/397 regions are negative. Negative-pair quantiles: p50 -69.8, p95 -18.4, p1 -209.5. Count with h >= -50: 53119;
  with h >= -100: 124826.
- What-ifs (counts still negative): no uncredited spread 145808; no OCV 156170; neither 87896.
- Late/early spread: 13-17 % of arrival at every depth (stage 1: 43.1/35.6 TT), 5.2-5.6 ps/stage. The proof STA has no
  timing_derate and a single NLDM lib, so the source is UNCHECKED (min/max slew propagation?). The AOCV table is charged
  on top of it. Possible double count with ONE SHARED MODEL "one variation model per segment".
- Worst tail (bk_sel 140/200, svc_12/13/8/9): early core tap t_bk_sel__clk_c3 (dsdv_bksel_q) is hung 3 stages below the
  LCA vs 17-21 for the registers. It is realised 868 ps early, but the declared core insertion offsets only 325 ps:
  over-early by ~540 ps (hang-mode quantisation). Worst pair without a core tap: -359.8 (112254 such negative pairs).

## 8. Check of the DIE-S81-9 kit-tap-window explanation on go13 (COORD 15:4x)
Main state: gen_phys lifted the 12.8d early-tap ban (DIE-S81-10), and plan_s10 carries clock.tap_window 180 ps.
Main die_sta_related kit_contract_hold, reproduced exactly by hold_classify.py (CHECKED):

| | zero-logic hold | kit contract W=180, nominal | kit contract + clock OCV |
|---|---|---|---|
| negative pairs | 171391 | 1279 | 5255 |
| W needed | n/a | 682.1 | 724.5 |
| W needed, pairs without an early core tap | n/a | 301.7 | 360.3 |

- The window explains the bulk: the 397/397 zero-logic negatives are the zero-data floor, and the kit repairs them inside W.
- It does NOT explain go13's -502 kit / -724 zero-logic. DIE-S81-9 on packed G needed W = 159.8 with OCV; go13 needs 724.5.
- Residual 1 (465/1279 nominal, 1789/5255 with OCV): early core tap pairs. bk_sel c0-c6 (c3 682) and fW*/fE* c0-c5 are
  over-early vs their kit offset (mean kit_offset -78 ps against tree skew +204 ps).
- Residual 2: register-only pairs with tree skew up to 302 nominal / 360 with OCV (> T/4 = 208). This is go13's region
  tree skew, worse than packed G. Regions: bk_sel 265, svc_12 59, svc_13 54, fW2_p1_b1 52, svc_8 37, lk_EN2 35.
- So the fix path is the tree (merge mode go15 + plan_s11 early taps), then the kit window, not die hold buffers.
  go15 gives the measured answer. ESTIMATE only, nothing changed.

## 9. Gate-mode STA on main 013a9a854 (CLK-INV-CAL-1 + cell-paths), dry run on go13; go15 runs the same script
Script: scripts/sta_gate.sh MAIN_WT PROOF PLAN OUT. It runs main die_sta_related with every signed S81 view that has
_tt/_ff libs (12 views) as --core-view, in gate mode (--core-insertion view) and declared mode, plus a labelled
DIAGNOSTIC run with --no-core-view-match-pins. Data: intel2:/srv/opentallas-scratch2/claude/die-s81-16/gate13.

| go13 (plan_s10), main 013a9a854 | TT setup | FF hold | kit contract (W=180) | early core taps |
|---|---|---|---|---|
| GATE (view) | -508.57 | -1049.05 | -502.09 (need 682.09; +OCV 724.52) | 1696 missing -> FAIL closed |
| declared | -106.97 | -724.05 | same | 1696 declared |
| DIAGNOSTIC declared, no pin match | -106.97 | -724.05 | same | real views on 4057 instances / 2181 taps |

- Gate mode: real-view pairs 0/178894. All 12 signed S81 views load, but none passes the default pin-provenance match.
  No S81 view directory has a provenance.json (kit.pins_file), and none of the 1696 early core taps (rom_elem_q, bf_col,
  bk_sel, ...) has a signed view yet. The gate stays FAIL closed until the CORES-EARLY views land with provenance.
- Main declared numbers are identical to the pre-CLK-INV-CAL-1 run: S81 already used --clock-cell inv2.
- Diagnostic real-view pairs (58408): TT setup +86.16 (0 neg); FF hold -204.05 (25242 neg; worst svc_12 dsdv_svc_sx_hrow
  -> budget, damage 224); both-real worst -96.6 (273 neg). This is the same tree-skew tail as section 8.

## 10. Early-tap re-estimate (CORES-EARLY-3 insertions) and sink-centroid entry (COORD dfd33a253)
Re-estimate, CHECKED arithmetic on UNCHECKED plan-model insertions (plan_event_s11.py on plan_s10 5f014a8d3554, then est_s11.py;
the 285/285 rerun reproduces plan_s11a 82b068249b56 byte for byte). Outputs are in intel2 die-s81-16/re391/.

| tap insertion TT (rom / bf_col) | early instance taps | sink hist <50 / 50-100 / 100+ | rom early TT | bf_col early TT |
|---|---|---|---|---|
| go15 = plan_s11: 285 / 285 | 1696 | 1491 / 167 / 38 | 35.0 | 35.0 |
| centre-entry slices: 390.9 / 282.5 | 1696 | 627 / 1031 / 38 | 140.9 | 32.5 |
| sink-centroid slices: 365.2 / 194.7 | 1240 | 171 / 1031 / 38 | 115.2 | not early |

The histogram moves: go15 under-advances the 864 rom taps by 80-106 ps TT. go15's rom-pair hold/setup are diagnostic, not gate.

Sink-centroid entry: branch claude/die-s81-16-entry-1028@dd944eb33c, on CORES-EARLY-3 0729bf9579.
- core_family_slice gets an opt-in family `entry` (per member). The default stays the centre, so default runs are byte-identical.
- families_r13 dv_misc sets bf_col and rom _gb to sink_centroid. Tests: 14 PASS.

Slices ran on the same census (intel1 die-s81-16-entry/w). Renders viewed.
- bf_col: entry (225.1, 99.4) -> (425.1, 99.2). L1 legs drop from 168-220 um to 20-39 um and TT drops from 282.5 to 194.7 (FF 145.1). The window stays at
  57.7/47.8 FAIL. It is set by the about 50 W outlier sinks on L4 legs up to 285 um, not by the entry. The converter still fails
  (unequal-count tree model target FAIL).
- rom _gb: entry (255.4, 110.7) -> (194.9, 123.0). TT 390.9 w22.6 -> 365.2 w19.8, FF 293.0 w22.7 -> 273.6 w17.3, so both windows are now <=20.
  The converter fails the same way as the centre run, mp_ck_T00_br with no free legal site within 20 um of (71.28, 152.82). That is a site issue
  on the probe floorplan, not caused by the entry.
