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
