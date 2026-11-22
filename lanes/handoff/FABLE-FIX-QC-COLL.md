# FABLE-FIX-QC-COLL handoff (Fable; owns QC coll_core end to end since 11-21 19:25 PST; successor of FAM-QC-COLL-R3 for coll_core)
Work dir: epyc7 /srv/opentallas-scratch2/claude/fable-fix-qc-coll (an/ = analysis + solver, pkg/ = composed plans, pk1/ = private bind, reset/, faultgen/).

## Method (close by construction, measured on the pkit10_wall placement)
- an/grp.py: group-level register-to-register reach through ALL logic (not only zero-logic links): 9,089 captures over 405 um in 312 group pairs.
- an/solve.py + cfg3.json: every reg-to-reg connection is a constraint L1 <= 370 um (330 to a macro box); soft flops move by constraint projection;
  result 14,516 violated edges -> 926 (20 pairs, list in an/s3/residual.json). Seats for ALL 49,530 GPL-placed flops = plan relay_sites (FIRM, 0 cycles);
  hook-placed flops (ring, face, reset relays, stations) are untouched.
- Stations by measured length (+cycles): rec_tx_s0 1->3, rec_tx_s1 0->2, rec_tx_s2 0->2, flt_o 0->3, fltv_o 0->3 (per-bit seats, sites=float),
  io_collective__fault 0->3 as three parallel OR groups (kit_istations or_groups, main 2c3fa5fd9727).
- Reset: the u_rrl_221 groups are a 3_place read artefact (reset_taps.tcl re-points leaves post-place, max 91 um); only 4 seats for the two face reset syncs.
- Residual after seats (needs RTL stage or a core move, not in this package): hi_q/lo_q -> g_pf fold slices 254 bits at 411 um (box distance),
  tbc/pe_q <-> g_pf_3 6 bits at 558 um, PIN shr_p_rx_i -> landing ring sd_c 467 bits at 441 um (ring structure).
- relay-mid: QC chain regex is on main 00377e9dc84a (default for qwen_compute); on coll_core every chain flop is seated, so the hook has nothing left to place.

## Package
- compose: an/compose.py PLAN_IN PLAN_OUT an/s3/seats.json reset/rows_reset.json faultgen/run1/row.json ROWS.json (idempotent wall respace included).
- pkg/plan_v3p3_coll.json = V3p3 f5d51696a2eb + package; pkg/lat_v3.json = same after gen.py latency (13 lanes change, 1921 lanes).
- pkg/plan_v2.json / lat_v2.json = V2+wall base for the private proof. Needs tools >= 2c3fa5fd9727 (schema key or_groups).
- Every coll_core kit: OT_KEEP_WIRES += ot_reset_sync:reset_pipe qfd_static_ch546:r_reset_meta.

## Live units / waiters
- see the posts in lanes/posts/FABLE-FIX-QC-COLL.md (latest line wins).
