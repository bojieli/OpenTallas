Qwen KV/system die bound by tools/die_plan/bind.py (BINDER2 10-23, rebind kv35)
plan: KV v3.5 claude/kv-p5-1023 @d7096700e physical/die_plan/qwen_kvsys/die_plan.json (+ lat_v35), plan cell conns
bind/plan_cell_conns_v34.json (rev @2d9f44504), plan rewires bind/plan_rewires_v34.json (@a73f158f5: astk/ectl relabel,
S hsl orientation -- these CHANGE FUNCTION and need the token benches). As-built: rtl6 qkd die @e33504a6f (+ rtl/lib
ot_dp_id / ot_dp_efault). Recipe ../asbuilt_binder2.json (reducers_keep_plan_contents, AND reducer for the serdes tx_up
join, reset spines, rewires, plan cells). bind.f paths relative to src e33504a6f overlaid with d7096700e
physical/die_plan/qwen_kvsys + this directory.
rtl/: partition modules (original leaves unchanged), qwen_kvsys bound top, bind_cells.sv; kv_hard_models.sv = the PHY
hard-macro models of kv_bound.  Latency: the plan table (lat_v35) incl. its pads (L637/L1456/L1490 8 cycles); no
land_align pads (see ../bus_groups_binder2.json.gz for the as-built groups).
verify_report.json: PASS -- 3,359,267 of 3,359,268 leaf-input bits identical to as-built or plan-driven (1,935), 1 glue
path bit, 0 unbound / tied / undriven / multi, lint 0 errors.  port_bind_strict.*: tools/die_port_bind.py strict PASS.
Open (G3, not functional): 11 type splits (per-quadrant clock-domain names, per-instance width packing).
