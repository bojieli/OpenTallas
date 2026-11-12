# QC s28 item 1 = s27 + sink bins on the QC density-tap types (QC-EVENT-S28, 11-12)

Plan: `plan_of_record/plan_qc99_s28.json` (sha 2f0c17d5f1a3). Base: plan_qc99_s27 820f14a689b7 (claude/qc-s27-vis-1111@9024de9d66).
Sidecar: `sidecar_pv_s28.json.gz` (sidecar_pv.json sha 38a30992accc; s27 27b0eca895ef). r8 table unchanged (r8_sw2.json 571c5b26bb1f).
Bind manifest: asbuilt_sw2_pv.json 5ef173b0f491, unchanged; this is the manifest without the st_b substitutions.
DO_NOT_COUNT: plan event only, nothing built.

## Class
HOLD-TAP-SPLIT (VISLAYOUT2-QC suc-hold / suc-hold-2; DIE-QC-97 hc0 / PLAN-GEN-RULES rule B). A density-tap type without
clock.sink_bins_file plans its taps from the plan's face, ft and station sinks only. That is 15-40 % of the netlist
registers on the st/fe/fw/su_c/ctl types. The kit's nearest-tap + cap split then leaves taps over the 1200 cap, and
station pairs end up on taps with 400 ps of tree difference (sle_su_c FF hold -410 ps).

## What changed (30 types; clock keys only, no core, RTL, bus or station change)
- `clock.sink_bins_file` = `plan_of_record/sink_bins/<type>.json`:
  - 14 types: the PGR rule-B bins already in the tree, carried byte-identical.
  - 15 types: new bins from each row's own latest `3_place.odb` (`scripts/sinkdump28.tcl`, all input ITerms on clk / clk_t<i>,
    10.8-um bins). sle_su_c's file is byte-identical to VISLAYOUT2-QC's (the same dump reproduces it exactly).
  - slw_sc_v2: no placed DB in its current form. Bins come from a SIBLING PROXY: slw_sc_v1__cl63e5a7a2 11-12 placement
    (same core, outline, glue and 17 ft slots) minus its extra x_fw_st_b slot (1,386 sinks), which gives 44,778 sinks.
- The density taps are re-derived. Forwarded-clock `landing_contract.pins[].source_clock_port/_tap` is re-pointed to the
  nearest new tap (the apply_vis_resite rule).
- `landing_contract.collector_tree` is re-solved with added_tap_recentre.republish (plan + sidecar). 8 su_l0/su_l1 sidecar
  copies already differed from the s27 plan tree; they are kept, because the bind walks the plan tree.
  collector_reattach then gives +0 collector cycles on all 30.
- slw_su_l1__cla2a78701: the bins tree came out one level shallower (6 -> 5). `reset.wavefront_min_depth = 6` keeps the
  published depth (precedent: sle_su_l1__clc6d66f5b).
- START / local-reset relay names re-anchor by site at bind (reset_anchor.resolve, same depth).

## NOT adopted: slw_su_c__cl19bb38ef (stays as in s27)
Its only placed DB (11-09) is stale: 3 cores have moved since, by up to 726 um. The bins were built from its own netlist
at its twin sle_su_c's 11-12 sites; they are in `evidence/not_adopted/`. On that tree the strict bind fails at
RESET_ANCHOR: writer START x_sc_o raw reset rst_rl_62 (depth 3) has no depth-3 relay within 405 um of its old site
(417.9 um) or of its stage (609 um). Fix: bins from its own s27 3_place.odb (the row is in flight), plus a START-stage /
relay-site event if the hole persists.

## Gates (s27 vs s28)
- schema validate, origin/main tools: 0 errors on both.
- G0, origin/main tools: 265 ERR on both, 0 new. WARN 366/366. The tap_sink_cap and xtap summary lines change wording only.
- G0C: 365 ERR on both, 0 new. WARN 571 -> 541 (22 new, 52 gone; evidence/g0c_diff.txt).
- station_lint: the same 3 NONMONOTONE advisory rows.
- Strict bind on s27 + bind-strict-src-1112r + readset dfe657faff + eq-triage aac9d8eba287 (bind.py cb732e489ee0):
  rc 0, 377 partitions, 1921 crossings, 790,393 bits, 0 errors, 0 R8_STALE.
- bus_groups.json 315252676904 = s27. A same-tools strict bind of s27 also gives rc 0. Real RTL diff s27 -> s28 (provenance and paths
  ignored, evidence/bind_realdiff_rtl.txt): only the .sv / reset_tree.tcl of the 30 types' modules + qwen_compute_bound_top.
- Tap histogram (evidence/hist_table.txt, `make_s28.py hist`; real sinks split by taps.assign = the clock_taps.tcl rule):
  0 of the 30 types have a tap over the 1200 cap on s28. On s27, 25 of them had taps over the cap. G0's nearest-tap
  (uncapped) view still shows slw_sc_v1 clk_t5 1540 and sle_fw_v2 clk_t4 1346; the cap move within 200 um brings both
  to <= 1200.

## EQ
The changes are clock tap, reset relay and collector re-solve only. No logic, port, bus, pipeline or collector-cycle
change (+0 on all 30), and every reset tree depth is unchanged.

Recipe: scripts/s28full.sh (`make_s28.py compose` -> `collector_reattach.py` -> gates + strict bind + hist).
