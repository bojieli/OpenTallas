Qwen compute die bound by tools/die_plan/bind.py (BINDER2 10-23, rebind qc10)
plan: QC plan @9d96cdb52 physical/die_plan/qwen_compute/die_plan.json; as-built: r56 qfd_die with the chain-end
leaves of @a9dea8962 (sources of record: git a9dea8962 rtl/ + physical/; bind.f paths are relative to that tree +
this directory). Recipe ../asbuilt.json; regenerate:
  python3 tools/die_plan/bind.py all PLAN --asbuilt physical/die_plan/qwen_compute/bind/asbuilt.json --out OUT
  python3 tools/die_plan/bind.py portbind PLAN --asbuilt ... --out OUT
rtl/: partition modules (original leaves unchanged), qwen_compute_bound_top.sv, bind_cells.sv; bind.f = file list.
UNPLANNED 0. land_align=cell: each sink leaf's inputs from one source partition keep their as-built relative timing
(ot_dp_dly pads; bind_latency.json landing_pads), except the collective SerDes / core<->face ports whose timing is
carried by regenerated parameters (param_regen.json, coll_regen.py: LS 376->389, face PHY 351/343/351, R 7/8/8,
PEER_R 8/8/7, bench args inside).  ../bus_groups.json.gz = R8 as-built bus / replica groups for the planner.
verify_report.json: FAIL only on 204 as-built TIED inputs left undriven (dvs fdn treq_i 108, sc_dn/sc_up 96; QC-P4
RTL), never tied; lint 0 errors (2 waived as-built RTL defects listed); all other 2,723,858 leaf-input bits identical
to as-built (14 glue-path bits not connectivity-comparable).
port_bind_strict.*: tools/die_port_bind.py strict on the bound top: PASS (die-top level; the 204 undriven bits are
inside partition modules and are counted by verify).
