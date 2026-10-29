# TOK-QC-2 (2026-10-28 20:49-21:4x PDT): ONE-QC strict bind on the QC plan of record ev_qc23pg - 32 -> 13 errors

Runs: epyc2:/srv/opentallas-scratch2/claude/tok-qc-2-1028 (bind2 = elab reuse of TOK-QC-1 bind1, bind3, bind5).
Numbers are read from own logs/reports (CHECKED) unless marked.

## Plan of record (COORD 21:0x)
ev_qc23pg (intel2 die-qc23-1028/plan/ev_qc23pg.json, sha ad01d656b2b5, copied with its cores/ to the run dir) +
grpP region map (069b686645d4) + DIE-QC-23 g15 bind_clock (8f8d51a61aa2, 2525 D4 + 12 D8, verify 0 identity/loop
errors, margins 104.5/142.4 ps). Branch merges claude/die-qc23-pg-1028 (PG `fields` schema).
Event (mk_ca_event.py): 119 types / 377 parts / 1921 lanes / 2525 CA ports, 15,968 strap bits, 12 D8 type buses.

## Fixes (strict bind 32 -> 13 errors)
1. RS pair (COORD item 2, GENERATOR rule): physical/die_plan/qwen_compute/bind/ca_pair_rule.py + test_ca_pair_rule.py
   (5 tests PASS incl. guard-violation and mutant). Both directions of each collective relay pair RS_j get the same
   count: shortfall placed as K+1/sched_lat+1 steps (one per non-tree hop, largest high-guard room first, >= 100 ps kept),
   then count_align_bind.verify re-run. RS1/RS2 core->face 8 -> 12 = face->core 12 (4 steps each), RS0 10/10
   unchanged; verify identity/loops 0, sim margins 104.5/142.4 ps = g15 unchanged. coll_regen RS = [21, 23, 23] (bind5).
2. R8 table: the main QC table (physical/die_plan/qwen_compute/r8, derived on an older plan) was stale
   (R8_STALE x30 CB16 member; CS_RXV seam: as-built rx_v 2 vs slot 3 lost -> PARAM_REGEN "shift by [2,3]").
   Re-derived with tools/die_plan/r8.py pads (defaults) on the current bind2 bus_groups -> results/tok_qc_2_1028/r8
   (7898 members, 1263 classes, 2717 padded, 959,423 pad flops, max pad 20; R8 check PASS: 1727 groups 0 unequal,
   0 inversions, 0 types conflicting) + asbuilt land_r8_strap_pads (OWNER 10-28 opt-in) -> 0 R8 / PARAM errors.
3. CB16 (COORD item 1): cb16_pads.py now emits INNER:<part> members for an intra-partition early leg ->
   qc_cb16_pads_tokqc2.json (from bind3): 311 members, 192 INNER, 841k pad flops (old meth table 716k).
   OPEN: INNER pads differ per INSTANCE (2/4/5 inside one type: upstream CA crossing latencies differ per instance) ->
   12 TYPE_SPLIT errors (119 -> 144 types). Proposal (ASK 21:2x): strap-count delay bank for INNER pads in
   bind.py r8_strap_sites (shared tool, ROOT-MERGE).
4. flt_st_a_i (item 3): still present on ev_qc23pg (type sle_fw_v1__cl02c0b715 = sl_E0_fw + sl_E4_fw). The 12 plan
   hops sl_*_st_a.flt_o -> sl_*_fw.flt_st_a_i have no RTL counterpart (bound st_a fault u_r0.fault -> u_ctl.stn_fault;
   u_fdn has no fault pin). Recorded plan delta TOKQC2_DROP_FLT_ST_A=1 in mk_ca_event.py (ports, lanes, latency,
   cland clock ports, u_pstn buses) = ASK 21:14 DEFAULT; DIE-QC-24 to take it into the plan of record.

## bind5 (current best; recipe asbuilt_tokqc2_ca.json, event with the flt delta)
377 parts, 144 types (12 splits), 1921 crossings, 792,661 bits, 0 unbound/tied/undriven/MD, 13 errors:
12 TYPE_SPLIT (item 3 above) + 1 EMIT: `wavefront core reset sle_su_c/u_suvm_u_vm8q_u_bt.rst_n: expected one bound
leaf, found 0` - the plan (54a1 and ev_qc23pg alike, K2b "signed SU views bound") resets SU hard cores inside
u_suvm (qfd_dv_s8x_vmr/crh/prog/btab, qfd_dv_s5_su8_rst3), but the bind elaborates qfd_dv_s8_suvm_rp1 as ONE leaf.
Tried: dissolve qfd_dv_s8_suvm_rp1 + qfd_dv_s8_vm8q_rp1 -> 201 UNMAPPED glue cells (map asbuilt_map_p6 has no
region for suvm glue) + plan hard-core module names differ from the RTL (u_cl/u_ch = qfd_dv_s8_crh_rp1 vs plan
qfd_dv_s8x_crh). -> needs the DIE-QC owner's SU bind form (map + recipe). No RTL emitted -> verify/portbind not run.
