# FALLBACK-HEAD (s81_head landed fallback) job list

## [FALLBACK-HEAD 2026-10-26 18:30 PDT] 16 ring-rebuild kits: NOT SUBMITTED (structural blocker, no job running)

Source claude/fallback-head-1026@eb56dcd125. Jobs submitted: **none**. Live units: none. Run data: epyc1:/srv/opentallas-scratch2/claude/fallback-head-1026 (sl300, compose3).

I checked the kit path before submitting. Three prerequisites are missing; a kit without them would not contain rings.

1. **No RTL path that emits the rings for HEAD.**
   - Rings and fclk pins are emitted ONLY by the binder: bind.py with asbuilt.clock_landing_table, which goes through clock_landings.type_rtl/top_rtl.
   - main has no s81_head asbuilt/bind recipe. The only per-type HEAD kits so far (PROTO-KITS hd_turn_a/b) come from gen.py rtl/phys of plan wrappers, and those emit no landing hardware.
   - Owner choice for COORD: (a) a HEAD strict-bind recipe (PATH-S81 / TOK-SCHED HEAD8 spec items are still open), or (b) teach gen.py rtl to emit ot_dp_clk_landing from landing_contract.
2. **Emitter support for monitor=dataflow.** clock_landings.type_rtl/top_rtl and landing_place.tcl currently assume the reset-mode collector tree (tree=None crashes). Spec for the successor:
   - type_rtl: ring W+2 with d={cland_dn_fault_<b>,cland_dn_ready_<b>,<b>}. in_ok_b = q_ready && landing_ready_b && !landing_fault_b. local = AND of all landing_ready_b, registered.
   - Aggregate = local AND all in_ok, registered local_registered_depth times.
   - cland_up_*_<o> = aggregate on the tree bus, local on the other outputs. The observer gets gate_observer(aggregate).
   - top_rtl: one wire pair per data port (src cland_up_*_<sb> -> dst cland_dn_*_<db>).
   - landing_place: bands + status points only.
3. **Reservations in kits.** gen_phys must take per-type reserved site rects. Inputs:
   - the union of sl300 tree sites over all instances, in the type frame (results/fallback_head_1026/sl300/tree.json `sites`, die frame -> P.to_type);
   - the compose_dataflow ring banks (e.g. hd_tile i at 17.28-261.36 x 362.88-373.68, hop 402.7/403).
   - No such kit key exists yet.

Successor order: (2) + (3) as code with tests (no jobs), then the (1) route COORD picks, then 16 kits via ot-run on epyc2/intel1/intel2 (<=400k cells, honest --mem). After that come ring-window STA and die STA with --spine-tree sl300. OPEN: hd_ctl observer RTL ports.

## [FALLBACK-HEAD-2 2026-10-26 18:48 PDT] (1)+(2) code READY; (3) BLOCKED (no s81_head as-built RTL); (4) NOT SUBMITTED. No job running.

Branch claude/fallback-head-2-1026@ba603056a (base eb56dcd125). All numbers UNCHECKED.
- (1) 70cf944c6: clock_landings dataflow monitor, opt-in via collector.monitor=dataflow (reset mode unchanged).
  - Ring W+2 = {cland_dn_fault_b, cland_dn_ready_b, b}. in_ok = ring ready bit && landing_ready && !landing_fault.
  - Aggregate is registered local_registered_depth times; each output pin gets its own output register (tree bus = aggregate, other buses = local).
  - The observer gets the aggregate via gate_observer. An OPEN observer fails closed.
  - top_rtl: one status wire pair per sender pin. landing_place: bands + status points only.
  - 5 new tests; 48 landing/collector/verify/s81_head tests PASS. Landings() accepts the real compose3 plan + sidecar (428 rows, 16 types).
- (2) ba603056a: gen_phys key clock.reserved_sites_um plus feeder tools/s81_head/fallback_reserve.py.
  - die_clock_tree rects become hard blockages (die_islands rule). landing_ring_bank rects are GPL-only blockages after the rings are FIRM and are released before DPL.
  - landing_placement avoids the hard holes (opt-in). Key absent -> kit byte-identical. 9 tests.
  - sl300 2393 sites -> per-type unions (hd_tile 600 rects / 2178 um2). 0 on hard cores, 0 boundary-spanning.
  - 8 hd_tile tree holes sit inside ring bank i (28.0 um2 = 1.06 % of the bank). They stay hard and the ring packs around them.
  - Reserved plan: epyc1:/srv/opentallas-scratch2/claude/fallback-head-1026/reserve2/reserved_plan.json (report also in results/fallback_head_2_1026/).
- (3) BLOCKED. bind.py strict needs an as-built die netlist (asbuilt.netlist/top). None exists for s81_head on main, r6 5e6a469de, codex/head-source-closure-1025, head-xb-main, head8-fixedclk, s81head-0733 or head-master-0733.
  - The plan content modules ot_s81hd_ctl (hd_ctl), ot_s81hd_mesh_ep (hd_mesh x3), ot_s81hd_host_ep (hd_host) and dsdv_slice_lepw_mu.LP (hd_lep0N) have NO RTL. ot_s81hd_ctl exists only as the hsf0_reference archive.
  - So a port-bind PASS is impossible without stubs (banned). The hd_ctl observer ports also stay OPEN.
  - r6 elemB 352-pin abstract is inside hd_tile, whose RTL exists, so it is not the blocker.
- (4) Not submitted: kits without the bind carry no rings.
