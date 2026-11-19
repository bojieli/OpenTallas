# FABLE-TYPE-REDUCE-QC handoff (owner order 11-19: cut QC types only where closure gets faster)

## 11-19 01:5x PST  Step 0 speed test: NO QC family passes as a template build now. One free merge found.

Inputs: live plan N4.3 (epyc9 kw45/snap_qwen_compute/qwen_compute_n43_s1, zz_s29_qc103_s4q9n43.json), bind
kw45/qcbind_pin_eb1e73448bd0_s4q9n4/bind_s29q103S4Q9N43BQ, census_qc.json, kit_wave status 01:2x, fleet TT scan 01:2x
(/tmp/ffq_all.sh /tmp/ffq_c3.sh on intel2, 89 live route jobs), AGIdock index. My scripts were short read-only plan/bind diffs
(rtx-pro session scratchpad); rewrite from this note if needed.

### What the 133 -> 73 census number is made of (measured on N4.3)
39 families hold 104 types = 44 (logic, outline). Three split mechanisms, none is pins / faces / orientation:
- __cl (clock_landing_plan.py:1051 and 1222; cohort signature = landed in/out sets, monitor children xy, up seam, ca_relay, CA mask):
  about 85 types. Plan pins and outline are identical in a family, but the bound wrappers are NOT near-identical: sle_ctl cohorts
  differ in 1,900-6,600 of 6,300-9,000 wrapper statements (reset collector tree relays, cland monitor bands 2 vs 3 vs 0, rst_o
  exports, strap ports, and the landing pad chains u_pd<D>_<bus>_<bit> whose depth D is baked per position: cl372cea1c 11/14/7/6 vs
  padE0 10/25/8/5). n_pad differs per cohort (sle_fe_v1 207 vs 188, slw_hc1 217 vs 233). cbn_q00 cohorts also differ in cland
  hard-core modules and tap mode.
- __pv (param_class_split.py; logic parameter values per instance, HI_PAD / RD_PAD pad depths): 15 types in 6 st_a/st_b families.
- __pad (r8_strap_pad_max, sle_ctl x3): same plan, pad depths differ in the bound RTL.
So the position-specific part is pad depth (lane latency) + reset/monitor tree, inside the type. QC is abutted: there is no street to
move the pad flops into (slw_fw 56 k) without a re-floor.

### State now
- Signed, any plan: about 30 QC types (103 unsigned at 23:18). They keep counting.
- All 133 types have a live N4.x wave row (ENQUEUED/RUNNING). About 27 are in detail route or abstract with TT >= -42
  (hc0 x3, sc x8, hc1 x2, st_b x6, su_l1 x4, su_l0, fw x2, coll_s, glue); about 16 more are in GRT with clean CTS TT.
- Siblings pass or fail together (TT ps): sc +2..+62; hc0 +17..+25; hc1 -3..+6; slw_st_b +10..+38 (one outlier cle6023ec2 -210, a
  type with no param_set, owner FABLE-FIX-QC); st_a x11 -167..-273 (N4.3 rows just applied); sle_ctl x7 -86..-109 (pad-chain hook
  just relaunched); cbx +11..+25 (one -15). No family has one clean variant the others could reuse.

### Speed verdict per family group
| group | types -> est | verdict | reason |
|---|---|---|---|
| sc, hc0-3, su_l0/l1, fe, stm, st_b (22 families, about 52 types) | -> about 24 | SKIP | setup-clean, in route / near gate or signed; a template renames the types, changes the die transport fingerprint (BIND-CHECK 133/133, as on N4.3) and restarts every kit (8-20 h each) for no fix |
| cbf/cbn/cbx (5 families, 14 types, 143 inst) | -> 6 | SKIP | CTS +17..+30, in GRT; cohorts differ in cland cores, taps (density vs explicit), monitor bands; a superset is a new clock design on the largest kits |
| sle_ctl (7) | -> 1..4 | SKIP now | all 7 share one failure class and one fix (OT_PAD_CHAIN_SITE, relaunched 00:5x); cohort wrappers differ 25-75 %; a merge needs strap-selected pad depth on every pad bus (RTL + bind) |
| st_a (4 families, 11 types) | -> 7 | SKIP template, 1 FREE MERGE | N4.3 st_a rows applied 01:03, kits relaunching, proof kit pk_sta running; a second event now restarts them again |
| fw (sle/slw fw_v1/v2, 9 types) | -> 4 | SKIP | flt_wo rows are already one row set per family, next delta; cohorts differ in 20 k pad chains |
| su_c, coll_ft | | SKIP | 2 types each; coll_ft has two outlines; su_c in flight with a fix |

Cost, template path: generator (cohort superset + role-named taps + strap pad depth) + bind + G0/LATCHECK + die clock rows, about
1-2 days, then a die-wide strict bind (two-pass, hours) and a restart of every merged family, plus new risk in the superset (max pad
chains and all monitor bands in every instance). Per-type path: kits already in flight, fixes already applied per family by regex /
item_env; the QC kit count is not what limits the fleet. A template saves compute per round (about 60 kits), not closure time.
Not faster -> not built.

### Free merge (no build, no template)
sle_st_a_v2__pv4242de79 (sl_E3_st_a) == sle_st_a_v2__pv30dda31f__pvd2ec7769 (sl_E1_st_a): bound RTL identical after the type name
(sha 9ef6a8b653, 284 k chars); plan record identical in 7,247 of 7,255 leaves, the 8 others are names and notes. The pv split is
stale. Rows: lanes/handoff/FABLE-TYPE-REDUCE-QC-rows.json. For QC-PLAN-R3 with the next st_a event (it changes the type list, so it
rides on the bind of that event; no event for this alone). Until then a sign-off of either one is the same layout; pk_sta
(pvd2ec7769) proves both.

### When a template does pay (for QC-PLAN-R3 / COORD; not started)
At the next event that restarts all QC kits anyway (re-floor or freeze event): (1) pad depth by parent-tied strap on every landing pad
bus (removes __pad and most __pv: about 18 types); (2) cohort superset where cohorts differ only in monitor-band count and rst_o
exports (hc*, sc, su_l*, fe, fw: about 25 types). Flag name reserved: partition_types.<family>.type_template: true. Nothing on main.

NEXT: nothing running, no waiter, no kit or wave row touched. Reopen only if COORD orders a die-wide QC restart event.
