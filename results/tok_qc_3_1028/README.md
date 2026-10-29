# TOK-QC-3 (2026-10-28 21:4x-22:5x PDT): INNER strap-count bank + SU split -> ONE-QC strict bind 0 errors on ev_qc23pg; ev_qc24 recompose

Runs: epyc2:/srv/opentallas-scratch2/claude/tok-qc-3-1028 (bind6 .. bind11, qc24plan = copy of intel2 die-qc24-1028/plan
with cores/ resolved from die-qc23-1028/plan/cores). Numbers are from my own logs/reports (CHECKED) unless marked.

## 1. INNER strap-count delay bank (shared tools/die_plan/bind.py, COORD 21:38 YES) -> branch claude/tok-qc-3-innerstrap-1028
Opt-in `asbuilt.land_inner_strap_pads`. Intra-partition edges with the same source leaf.port[bit] in every instance of a
type but a per-instance kept depth (QC CB16 INNER pads) -> fixed ot_dp_dly(base = min) + ot_dp_dly_cnt #(DMAX = span) with
a parent-tied `strap_r8pad_<site>_in` count (same r8pad manifest, G0 tie-value audit, r8_strap_lec as the OWNER 10-28 R8
sites). Tests test_inner_strap_pads.py (4) incl. MUTANT: count one low fails the tie-value audit and the iverilog bank
latency != kept depth. 362 bind/r8/strap/count tests PASS.
QC effect (bind6, ev_qc23pg event of TOK-QC-2 + flag): 144 -> 119 types, 13 -> 1 errors; 24 INNER sites / 12 types /
12,336 bits, max span 5.

## 2. SU wavefront reset (DEFAULT (a), COORD 21:38 / DIE-QC-24 22:31)
Recipe asbuilt_tokqc3su_ca.json = tokqc3 + dissolve qfd_dv_s8_suvm_rp1, qfd_dv_s8_vm8q_rp1 + map asbuilt_map_tokqc3.json
(= asbuilt_map_p6 + rule `dvs_*.u_core.u_sub.u_suvm\..*` -> sl_*_su_c; DIE-QC-25 owns the map: take it or replace it).
Needs a fresh elab (bind9, 46 s). Dissolve moves the SU sinks inside u_suvm -> the r8 table is re-derived on bind9
bus_groups (results/tok_qc_3_1028/r8: 9050 members, 1491 classes, 944,759 pad flops, max pad 20; r8 check PASS 2051
groups 0 unequal, 0 inversions, 0 types conflicting).
Tried and dropped (recorded): moving the core-reset target to the u_suvm leaf pin (plan reset tree comes from the btab
pin table; the clock-landing collector then references removed reset relays, `rst_rl_63 absent`).
crh: plan hard core u_cl/u_ch = qfd_dv_s8x_crh (signed kit) vs RTL qfd_dv_s8_crh_rp1 (header: UNCLOSED successor, MIF=1
+1 cycle) - did NOT cause a bind error; DIE-QC-25 owns the rename/kit.

## bind10 = current best on ev_qc23pg (TOK-QC-2 event): STRICT BIND 0 ERRORS
377 parts / 119 types / 1921 crossings / 790,393 bits / 0 errors, unbound, tied, undriven, MD; 11,568 straps.
verify: Yosys elaboration of the bound top OK (verify/bound.json), then clock_landing_verify CRASH:
`check_reset: tree['relays']` on None - the sidecar collector has tree=None for the soft type slw_hc3__cld86a7ad4
(sl_W1..W5_hc3, sl_E5_hc3: clock_landing_plan sets tree only for `active` landing parts) while _check_origins checks the
count-aligned start relay rx (u_cland_rstart_rx) in that partition. Shared-tool bug (clock_landing_verify or the active
set in clock_landing_plan); the bind emitted a reset tree there (48 rst_n_t* lines).
portbind: FAIL `child ot_qwen_w12_matvec_part AMBIGUOUS` (rtl/hdc/ot_qwen_w12_matvec.sv vs
rtl/physical/a0_rc14_selected_2000/ot_qwen_w12_matvec{,_land32}.sv differ in ports) -> recipe `prefer` for the A0 source
of record (elab also lists romleaf_rr ambiguous between a0_rc14_selected_2000 and rtl/physical).

## ev_qc24 (COORD 22:3x: plan of record e12e39da0fae) -> event results/tok_qc_3_1028/event (plan ce3e65a0af85)
mk_ca_event.py (TOK-QC-2 script) + table delta: the 12 st_a fault rows of grpP absent from ev_qc24 are pruned (assert:
exactly those 12) + 7 stale per-type edge clocks fclk_in_flt_st_a_i dropped. Compose: 119 types / 377 parts / 1921 lanes /
2525 CA ports, 15,968 strap bits, RS pair 12/12, CA verify 0 identity/loop errors, margins 104.5/142.4 ps; 0 flt_st_a refs.
bind11 (ev_qc24 event + tokqc3su): 1 error `EMIT cbf_q00__cl1b5a6458: fclk_out_bc_o01 contract source_clock_port clk_t24
is not an input port of the type`. The input plans agree (ev_qc23pg and ev_qc24 both have source_clock_port clk); the
compose on current main (merged 6a56d58118) now writes landing-contract source_clock_port = the tap clock (clk_t24/26/27)
and drops source_clock_tap -> a compose-vs-bind interface change on main (UNCHECKED which commit).

## Bench note (COORD FYI Verilator `<= #d ck`): my only bench is the iverilog unit test (free-running `always #5 clk`),
no delayed clocks - not affected.
