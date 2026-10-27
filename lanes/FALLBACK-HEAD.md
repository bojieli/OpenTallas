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
