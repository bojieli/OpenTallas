2026-10-29 18:56 PDT. Viewed review.png + ring_review.png before routing.
GQL: retained density26 placement, face registers on perimeter, central independent
clock/reset island, no macro walls. Original DRT-0255 mp_isl0_ck_i x66.96/105.84;
move four M5 island BTerms x66.96/71.28 ->68.04/70.20 (existing REBAL-2 +/-1.08
form). All eight RTL/synth artifacts byte-identical with qualified originals,
all cells/nets/tree/data pins unchanged, +0 cycles. PASS-COND route-access trial.
Two original FAILs preserved; no signoff claim. Jobs epyc2 codex-hbm-gql-1849
units3471617/3472590, run_dx108.log + run/logs/asap7/*/base/5_1_grt.tmp.log.
First runner starts3423294/3424660 stopped only own exact docker containers to
avoid redundant LEC, then geometry-only resume uses original qualified netlist.

RING: retained A2 placement with dense W/N/E boundary registers and distributed
internal dataflow/clock buffers; no macro wall. Existing route DRC0, timing and
clock pass; residual slew89/49 only. PASS-COND post-route drive-repair trial using
existing shared post_route_drv scripts (source17495b11ea); netlist timing/clock
qualification repeated by that flow. PG and pins unchanged. Uses actual routed
SPEF, guarded MM hold repair, frozen sink masters/clock checks. +0 cycles.
Old NOT SIGNED verdict retained. Trial epyc2 codex-hbm-ring-prd-1856/m15.
