Qwen compute die bound by tools/die_plan/bind.py with land_align=r8 (BINDER3 10-23, rebind qc11; COORD 16:58 R8 SOURCE OF TRUTH)
plan: QC-P5 claude/qc-p5-1023 @c0152774b physical/die_plan/qwen_compute/die_plan.json (= plan 9d96cdb52) +
r8/qwen_compute_r8_landing.json (874,976 pad flops, made by PLAN-TOOL3 r8.py from BINDER2 bus_groups b1e14ae54).
as-built: r56 qfd_die + QC-P4 chain-end leaves @a9dea8962 (bind.f paths relative to that tree + this directory).
Recipe ../asbuilt_r8.json (= ../asbuilt.json with land_align r8):
  python3 tools/die_plan/bind.py bind PLAN --asbuilt physical/die_plan/qwen_compute/bind/asbuilt_r8.json --out OUT  (+ verify, portbind)
Landing pads: every r8 table member realised as ot_dp_dly after the sink partition's in boundary flop; stale 0 /
uncovered 0 (every crossing bit is in the table with the same source, as-built and bound depth). EXCEPTION: the 35
collective SerDes / core<->face members named by asbuilt.land_align_exclude get NO pad -- their timing is the
regenerated collective calendar (param_regen.json: LS 389, face PHY 351/343/351, R 7/8/8, PEER_R 8/8/7, as qc10); the
table pads 11 of them by 1..5, which would break coll_regen's one-depth-per-leg rule (bind_report lanes.landing_alignment
.r8_excluded).  r8_g0_check.json = r8.py check on this bind's bus groups: PASS except those 3 collective groups + 1
replica (sx0_valid coll_n 7 / coll_s 8).
r8_heads_check.json (../xt1_heads_check.py): u_tap.hw / u_tap.cid land at 6 on hc0..hc3 in all 12 slices (96/96);
head -> column go n_d all 2, s_d all 8.
verify_report.json: FAIL only on the 204 as-built TIED QC-P4 chain-end inputs (dvs fdn treq_i 108, sc_dn/sc_up 96),
left undriven, never tied; all other leaf-input bits identical to as-built.  port_bind_strict: PASS (74 masters / 388).
Verilator 5.050 lint (lint_split, 110G cap; the earlier 'lint 2' was OOM kill -9, not RTL): 0 errors.  Bind 870,392 pad
flops (table 874,976 minus the excluded collective members).
G3 kit RTL: bind.py kit-rtl PLAN --out <bind out> --type T [--instance I] -> <plan module>.sv wrapper + kit_rtl.f
(gen.py phys --kit-rtl T=kit_rtl.f).  QC types carry per-instance strap PARAMETERS (tile_id, sidx): one kit per strap
set (--instance) until the straps become pins; e.g. cbx_q10 / c_E0_bf_10 lints 0 errors (39 files).
