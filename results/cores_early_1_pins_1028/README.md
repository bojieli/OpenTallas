# CORES-EARLY-1 task 3 (2026-10-28): S81 pin mismatches rstg / payload536 / vq

CORE-VIEWS-1 (claude/core-views-1-1028@c264641576) found 3 S81 signed views whose pins do not match the plan
(die_sta_related.pins_relation): dsfd_rstg 216 inst (2 pins), ot_s81_sstn_payload536 660 inst (all 1074 pins
+-53/54 nm), ot_s81sl_vq 75 inst (view 830 pins, plan 702).

## Root causes (CHECKED: LEF rects / pin tables / RTL read from git)
- **dsfd_rstg, ot_s81_sstn_payload536 -- PLAN stale (abstract changed).** The plan tables inputs/core_pins/<m>.json
  were cut 10-23 by the CORE-KS rule (centre of the pin's largest non-M1 rect) from the pre-ECO planning abstracts
  physical/ref_tile/{s81net_rstg,s81_sstn_payload536}/views/<m>/<m>.lef. Those pins are deeper: payload536 N/S pins
  0.192/0.144 um (e.g. i[72] M3 0..0.144), rstg ck[0]/rs[0] carry a merged access stub (0.06..0.227 / 0.06..2.408).
  The S81-ECO-1 SIGNED views (cea0b97cf, 10-27) were written from the routed ODB with minimum-depth pin shapes
  (0.084 / 0.038 um). Same pin, same track, same edge; only the rect centre picked by the CORE-KS rule moved
  (N/S faces +-0.053/0.054 um in y; rstg ck[0] x 0.1435 -> 0.042, rs[0] 1.234 -> 0.042). The CORE-KS rule re-run on
  the signed LEF gives exactly the views' signed pins.json (0 differences, both modules), so the generator fix is to
  re-run the plan's own rule on the signed abstract.
- **ot_s81sl_vq -- KIT stale (re-sign needed, no plan change).** The signed view (S81-CORES-R23 10-27, MM successor of
  the r12 LFP kit) was cut from the 10-24 07:29 table (b3970b1af, sha 507be426, 830 pins) and its staged source has
  `input [255:0] y` (unpacked FP32). OWNER DECISION 8 (a84140a61, 10-24 20:09) narrowed vq to `input [127:0] y`
  (packed BF16, unpacked at the input flop) -- that is main RTL; then LEAFPLAN moved clk/rst_n (af6b1f54d) and
  TYPE-REDUCE-2 (0ccde7a09, 10-25) made the one mirror-compatible template table ot_s81sl_vq_tpl.json (N/S V pins on
  M5, 702 pins). The view is signed on an interface the release RTL no longer has; a pin-table edit cannot fix it.
  Needs: re-kit from the current generator on main RTL + inputs/core_pins/ot_s81sl_vq_tpl.json, sign-off
  (TT setup, FF hold, DRV, routed LEC), export. The last tpl re-kit (289d52ccac3c, 10-26) failed FAIL_POSTCTS on
  the legacy GRT insertion gate and its kit was on retired epyc1.

## Fix (generator, no hand edits)
`physical/die_plan/s81/delta_signed_view_pins_1028.py IN.json OUT.json [--write-tables] [--report R]`: for every plan
hard core with a SIGNED view in physical/die_plan/s81/cores/views/<m>/: SAME when the kit was cut from the current
table (view freeze.json pins_sha256 == table sha256 -- the 9 already-canonical views); else the CORE-KS rule
(core_pins_gen.table) on the signed view LEF, pin set kept, written only if it equals the signed pins.json on every
pin (RULE-DIFF otherwise), KIT-STALE when SIZE or the signed pin set differs. Changed tables -> hard_cores[].lef/.lib
point at the signed view (FOLLOWS-VIEW keeps that idempotent for every plan sharing the table).
Tests: test_delta_signed_view_pins.py (5: stale abstract followed, kit-from-plan untouched, wider-interface mutant
refused, rule-diff not written, second plan repointed).

Committed: the 2 regenerated tables (dsfd_rstg.json, ot_s81_sstn_payload536.json). die_plan.json NOT edited: the
lef/lib repoint (19 rstg + 38 payload536 hard_cores on main die_plan.json; 31 + 84 on plan_s10) is the S81 die
owner's plan event: run the delta on the current plan (output copies on intel1
/srv/opentallas-scratch2/claude/cores-early-1-pins/{die_plan_main_delta,plan_s10_delta}.json). The pin match uses
only pins_file, so the gate is fixed by the tables alone.

## Pin match after (CHECKED: CORE-VIEWS-1 checks/match.py = die_sta_related.pins_relation, views unchanged, no re-export needed)
| plan | dsfd_rstg | ot_s81_sstn_payload536 | ot_s81sl_vq | other 9 views |
|---|---|---|---|---|
| plan_s10 before (CORE-VIEWS-1) | MISMATCH 216 | MISMATCH 660 | MISMATCH 75 | canonical 3106 |
| plan_s10 after | canonical 216 | canonical 660 | MISMATCH 75 (kit stale) | canonical 3106 |
| main die_plan.json after | canonical 216 | canonical 660 | MISMATCH 75 | canonical |
New tables: 0 pins off the kit track (core_pins_gen.ontrack, offset 0.108/0.012).

## Consequences (UNCHECKED)
- Frame partition kits that place these cores (col_h10 r0 frames) must use the signed view LEF when they are next
  generated (they otherwise see the deeper pre-ECO pins; the access point is the same track/edge).
- The vq view must not count as SIGNED for the release interface (pre-OWNER-DECISION-8 RTL).
