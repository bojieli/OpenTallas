Qwen compute die bound by tools/die_plan/bind.py (BINDER2 10-23)
plan: claude/qc-p3-1023 @ffdcc9159 physical/die_plan/qwen_compute/die_plan.json (+ qwen_compute_latency.json)
as-built: ../asbuilt.json (r56 qfd_die, main sources); regenerate:
  python3 tools/die_plan/bind.py all PLAN --asbuilt physical/die_plan/qwen_compute/bind/asbuilt.json --out OUT
rtl/: partition modules (original leaves unchanged), qwen_compute_bound_top.sv, bind_cells.sv; bind.f = file list.
verify_report.json: FAIL only on 5,927 as-built TIED chain-end inputs (left undriven, never tied; QC-P3 RTL CHAIN_END fix)
and 85 unplanned bits (coll/glue, QC-P3 next plan); everything else bit-identical to as-built (2,729,219 leaf-input bits).
port_bind_strict.*: tools/die_port_bind.py (strict) on the bound top: PASS (0 unbound/stub/width/unconnected/tied/undriven/multi; --prefer rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv for two same-name child copies).
