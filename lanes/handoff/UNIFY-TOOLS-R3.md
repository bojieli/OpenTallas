# UNIFY-TOOLS-R3 handoff (2026-11-20, started ~14:20 PST; succeeds UNIFY-TOOLS-R2)

OWNER priority: class merging tools. Work dir epyc9 /srv/opentallas-scratch2/claude/unify-tools-r3-work (W below);
lane clone epyc9 /srv/opentallas-scratch2/claude/unify-tools-r3 (cone tools, rtl, physical/common_flow).

## Done
1. class_merge prices the representative's OUT kit stations (main 796b3c1f6ec, tests test_class_merge.py 9/9).
   price_out_stations(): a lane leaving a re-typed instance whose class OUT chain (native_istations.kit_source_depth)
   is deeper than the member chain, that priced the member chain (fixed_cycles >= member depth) and that is predicted
   late (late_by_kit: bind cuts the source chain from the receiver pad only when fixed >= depth; a zero receiver pad
   gets the IN chain kit-built) gets fixed_cycles + latency fixed/cycles/natural += depth delta.  Runs inside merge();
   `--reprice-from PRE_PLAN` applies it alone on an already merged plan.  On QC ph5 it picks exactly the 5
   UNPRICED_KIT_STATIONS lanes (+7 cycles).
2. R8 re-derived from the ph5 bind bus_groups (tools/die_plan/qc_r8_pinned.sh derive, s29 pin): W/r8/r8_ph5.json
   (330 members changed vs the A4 table zz_r8_s29q103S4Q9N46V0EBQ.json).

## QC private proof (base A4+CBX plan_n46cbxm_r4_provider27 + R2 ph5 merges)
- W/ph6/plan.json = R2 ph5 plan + reprice (W/ph6/kp.json, 5 lanes) + slw_hc3 b_hw_i level-up on
  sl_E0/E4/W5_ctl__b_hw_ctl_hc3 (+3 cycles each, pad 3 = class pad; what pad_hoist --raise-cycles would do; W/ph6/level_hc3.json).
  Total vs ph5: E0/E4 hc3 lanes 12 -> 16, W5 11 -> 15, flte 4 -> 7, x_fw_fe_p2 14 -> 15.
- Bind script W/bind_core_r3.sh (= R2 bind_core_rs.sh + env R8_TABLE installs the derived table). Launch as plan job:
  `ot-run --mem 24 --threads 1 --plan-job bind --hosts epyc9 --dir W -- env R8_TABLE=W/r8/r8_ph5.json bash W/bind_core_r3.sh W/ph6/plan.json W/ph6/side.json 22a689dfc092 W/ph6/bind_r1 /srv/opentallas-scratch2/claude/unify-tools-r2-work/overlay/schema_preview.py`
  (a non-plan-job 64 GB request waits forever in the epyc9 memory queue).
- ph6/bind_r1: RUNNING (started ~14:36 PST). Result W/ph6/bind_r1.log, .rc.

## Composition with QC-PLAN-R5 (fabric V1, plan epyc9 .../qc-plan-r3-n41p/n46/v1_cbc/r5/v1a_r5_fabric_a_raw2_plan.json)
- R5's plan is on another base (A4 tree, 91k leaf diffs vs my base), so a row delta does not carry (43 conflicts:
  sle_ctl / slw_fw / slw_stm types differ).  Compose = rerun the tools on R5's plan instead; already done for the merge
  step (no bind yet): W/compose/m3_plan.json + m3_side.json = raw2 + class_merge sle_ctl (7 -> 1, 12 inst) + role-strap
  slw_stm + slw_fw (kit-priced 2 lanes +6 cycles there).  Next on that: strict bind with R5's script (v1a_complete_strict_r5.sh,
  needs the R2 overlay tools clock_landings.py clock_landing_verify.py count_align_bind.py landing_tie_children.py installed
  in launch/tools/die_plan, as bind_core_rs.sh does), pad_hoist --raise-cycles on that bind, re-bind, R8 derive, re-bind.
- W/plan_row_merge.py (delta / apply, 3-way per leaf, keyed lists) is private, not on main.

## Next
1. ph6 bind -> strict 0? then G0 (R2 g0.sh on the launch dir) and LATCHECK (in script).
2. netlist_inherit.py summary/prove on one merged kit's synth (bind.py kit-rtl -> gen.py phys -> run_kit.sh synth).
3. QC rows to QC-PLAN-R5 for V1 (cut ~09:30 PST 11-21).
4. S81 leaf class (s81.leaf_nogrowth_j4e): LEFT FOR NOW by COORD. It needs a class floorplan with feed-through superset
   windows first (rep lacks F00 ft-superset windows; R2 column-solver rows epyc9 .../unify-tools-r2-work/s81col not J6-ready).
