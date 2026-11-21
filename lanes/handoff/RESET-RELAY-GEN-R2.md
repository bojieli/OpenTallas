# RESET-RELAY-GEN-R2 handoff (succeeds RESET-RELAY-GEN-1530; updated 2026-11-20 PST, context past 310k: successor takes over)

Lane clone: epyc10 /srv/opentallas-scratch2/claude/rrgen-r2/src (branch rrgen-r2-nested; land with `cd src && python3 -I /srv/opentallas-scratch2/claude/rt/current/tools/fleet/ot-push-main`;
run tests with `python3 -m pytest -p no:warnings -p no:cacheprovider --basetemp=/srv/opentallas-scratch2/claude/rrgen-r2/pt <files>` in tools/die_plan).
Work dirs: epyc10 rrgen-1530/{r2_t72,r2_t56,leg_r2t72,leg_r2t56} ; epyc10 rrgen-r2/{qc_v1_p_h.json,scan_qc_v1.json,kv/}; epyc2/epyc9/epyc7 rrgen-r2/gd_<t>/ (geom dumps).

## On main (pushed, tests green)
- 93b5c48224 form N: hard cores NESTED below a bound instance -> plan key reset_pin_relay rows (+ relay_sites key
  {inst}.u_rst_pin_relay_{port}.g_r.r[s]); one D per top-level group; MR record has the pin name (geom_dump.tcl 5th field).
  bind/kit-rtl ignore the key (no call to stage); OT_BKSEL_L4 RRD RTL is the applier for bk_sel. NOT yet checked on the 7 bk_sel cores.
- 42eeacf87f legal relay sites: reset_tree._free needs a free row-high (0.27) x cell-wide (1.08) run; thin macro channels
  (S81 cl0cd90c0e rst_rl_137 at 219.58,1092.96 between u_ha/u_hb, 0.06 um sliver) are no site; push_off picks the nearest legal one.
  reset_leg_plan snaps stage sites likewise, re-checks hops (report site_snaps / snap_hop_um). Test with the exact numbers.
  A regenerated bind on tools >= 42eeacf87f seats the tree legally; for cl0cd90c0e that bind may need a deeper tree: moving the
  relay to the nearest legal edge x=332 would give a 382 um hop to the collector near (8,1150), so the tree must be re-solved, not patched.
- 803803f530 bank_reset_delta --landing TYPE=landing_placement.tcl: u_bin_<bus> position = centre of its u_cland_<bus> ring box, nearest tap,
  reset.bank_taps, 0 cycles (KV buses sited per port were `unplaced`).
- (pushing at time of writing; check `git log origin/main`) relay_site_scan.py PLAN [--types] [--out] (scan_tree/scan_plan; per type
  the illegal relays + nearest legal site + hop before/after) and lockup default: relay_depth rows carry lockup:true; kit_relay_depth.apply
  adds an ot_dp_lk latch (u_lk_xd_*) after each stage, receipt needs_cells; bind.py emits the same at bind time, appends ot_dp_lk cell
  (kit-rtl writes kit dir ot_dp_lk_cell.sv); reset_leg_plan --no-lockup = same edge; reset_pin_relay rows carry lockup too.
  FABLE-CLOSURE-1930 stop list: no more same-edge reset stages in volume.

## Rows: status
- S81 leaf t72 6->0 (+3 cycles), t56 5->0 (+5): computed on epyc2 attempt_17 / attempt_12 3_place geometry, NOT posted yet and must be
  re-emitted with lockup (rerun leg10.sh on rrgen-1530/r2_t72, r2_t56; default now lockup). t1: dump queued on epyc9 (rrgen-r2/gd_t1.log).
- (1) cl0cd90c0e row for S81-J6-ASSEMBLY: PENDING (no full J5/J6 plan reachable; kit at epyc10
  .../s81/224567138ab/items/col_h9_r0_p3__t1__cl0cd90c0e__pv8d734760/attempt_3, reset_tree.tcl line 183 rtr_place rst_rl_137). Run relay_site_scan on the J6 plan, post.
- (2) 14 KV u_bin rows (sys_c a7, hub_Wo a9, hub_Eo a3, pv v1 v1n v2 v2n v3 v3n v4 v4n v5 v5n v7): PENDING. Kits found (epyc7/8/2/9 ...KV-D25e3/items/<t>/attempt_N/gen/<t>, attempts in
  /tmp scratch kvgather.sh: sys_c 7, hub_Wo 9, hub_Eo 3, pv v1 4, v1n 4, v2 4, v2n 6, v3 5, v3n 12, v4 6, v4n 4, v5 4, v5n 9, v7 3). D26/D27 plan:
  epyc7 kv-d23-compose8/d26_raw/d26_contracts/physical/die_plan/qwen_kvsys/plan_of_record/plan_c.json (R3e a9f605cb1acf). Gathering to epyc10
  rrgen-r2/kv/<t>/ failed once (the tar stream got `ls` output mixed in: remove the `ls ... &&` from the ssh command; also create dirs via ssh).
  Then: bank_reset_delta.py PLAN <t>/b OUT REP --types <t> --landing <t>=<t>/landing_placement.tcl (b/<t>.sv = the kit rtl/*_bound.sv); check tap indices vs
  for_type(P,t) taps of the D26 plan before posting. Post to KV-PLAN-R2 (D27), cc OPUS-FIX-KV-PV-R3.
- (3) QC cb: 11 of 17 cb types without rows + cbn_q11__cl5cc92dfe 379 um leg -> QC-PLAN-R7 (V2, not R6): PENDING. QC V1 plan = epyc9 qc-plan-r6/v1/p_h.json
  (needs sibling files sink_bins/... that live in other lanes' trees, e.g. epyc9 /srv/opentallas-scratch/claude/qc-plan-r3-n4/tree_n4p1/physical/...: run the tool
  from such a tree or copy the plan next to a tree that has them; reset_leg_plan itself needs a placed geom (leg10.sh) per type, so use the newest QC cb ODB dumps).
- (4) plan scan: relay_site_scan on QC V1 failed ("128 types without a tree": missing sink_bins file, see above); KV D26 not run. Post results to each lane.
- Also pending: bk_sel check (dump epyc7 rrgen-r2/gd_bk.log; compare to opus-fix-s81-bksel-r4/rows_l4.py: 6 flops/core, hop <= 276), post nested rows to S81-J6-ASSEMBLY.

## The four proofs (private kit copies; none has produced a place/CTS report yet at last look 18:13)
lepe r4 place epyc10 oth-ubuntu-4060581-1795226367 (p10/lepe), t60 CTS oth-ubuntu-4060575-1795226367 (p10/t60), hub_Eo place oth-ubuntu-4060666-1795226367 (p10/hubEo),
pv place epyc7 oth-ubuntu-2363321-1795218686 (proof/pv). Read with rrgen-1530/rpt_sum.py (see RESET-RELAY-GEN-1530.md baselines: lepe async -456.1/WNS -644.4, t60 WNS -492.6,
hub_Eo -747.0, pv async -2,218.1). Report worst reset path + WNS before -> after to J6-ASSEMBLY / QC-PLAN / KV-PLAN-R2.

## Jobs in flight (ot-run; cancel only with ot-run --cancel <unit>)
epyc9 gd_t1 (geom dump t1), epyc7 gd_bk (bk_sel dump), the four proofs above.
