Qwen compute die bound by tools/die_plan/bind.py, land_align=r8 + QC-P5-TIE (BINDER3 10-23, rebind qc12)
plan: claude/qc-p5-tie-1023 @e3f313354 physical/die_plan/qwen_compute/die_plan.json (= QC-P5 9d96cdb52/c0152774b + 12 treq
lanes twinned with cmd) + plan_rewires_treq.json (class treq: 12 template-less edges, bits identity, stages from the
'beside' cmd edge).  R8 table: QC-P5 @c0152774b r8/qwen_compute_r8_landing.json + ../qc_treq_pads.json (land_r8_extra:
each treq hop lands with its cmd twin; made by ../treq_pads.py on this bind).
as-built: r56 qfd_die + QC-P4 chain ends @a9dea8962 + QC-P5-TIE @0cd1eebf3: dvs_(E1|E3|W1|W3) -> qfd_dv_s8_ce_l9h,
dvs_W5 -> qfd_dv_s8_ce_w5 (no sc_up_i), dvs_E5 -> qfd_dv_s8_ce_e5 (no sc_dn_i) (k79 sc2 dn0/up0 netlists).
bind.f paths are relative to that source tree + this directory.  Recipe ../asbuilt_tie.json:
  python3 tools/die_plan/bind.py elab|bind|verify|portbind PLAN --asbuilt physical/die_plan/qwen_compute/bind/asbuilt_tie.json --out OUT
Results: proof unbound 0 / TIED 0 / UNDRIVEN 0 (the 204 known bits are gone: treq 108 rewired, sc_dn/sc_up 96 removed by
the chain-end RTL).  verify_report.json PASS (2,723,870 matched, 0 mismatched), Verilator 5.050 lint 0 errors.
port_bind_strict PASS (80 masters / 388 instances).  R8: stale 0, uncovered 0, 870,428 pad flops, max pad 15; 6 Yosys
fault-OR cells renumbered by the re-elab matched by canonical name; 3 table members on the removed sc_dn_i/sc_up_i
(pad 0) recorded as gone_pad0.  35 collective members land_align_exclude (coll_regen calendar, param_regen.json: LS 389).
r8_heads_check.json: tap.hw / tap.cid land 6 on hc0..hc3 in all 12 slices (96/96); n_d 2, s_d 8.
treq_vs_cmd.json (compiler latency term): every treq hop lands with its cmd twin (tt_ctlm -> W5 8/8, slice hops 2/2,
offset 0); the 1 edge/slice earlier arrival (W5 0 .. E5 11) is the leaf-internal fdn->fup treq vs cmd difference.
G3 kit RTL: bind.py kit-rtl PLAN --out <bind out> --type T [--instance I] -> wrapper + kit_rtl.f (gen.py phys
--kit-rtl T=kit_rtl.f).  QC types carry per-instance strap PARAMETERS (tile_id, sidx): one kit per strap set
(--instance) until straps become pins.
