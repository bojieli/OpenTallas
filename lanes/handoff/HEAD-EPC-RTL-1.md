# HEAD-EPC-RTL-1 handoff (2026-11-15) - hd_host_e form B (register slice u_ski -> u_epc in_data)
- TO HEAD-99 (no live messaging path; COORD: HEAD-REMAP-1 has no owner, send everything to HEAD-99): put this delta into rp21z20NC prep / next re-prep.
- RTL: epyc7 /srv/opentallas-scratch2/claude/head-epc-rtl-1/src/rtl/dsrom_sys/s81_head/ot_s81hd_mesh_ep_core.sv, define OT_HE_EPC_ISLICE (2-entry slice, +1 cycle; default netlist unchanged). Patch script head-epc-rtl-1/patch_islice.py (idempotent only on the unpatched file).
- Plan delta: head-epc-rtl-1/hostE_formB.py PLAN_IN PLAN_OUT (adds the define to hd_host_e, lane coll_HOST1_d fixed_cycles 1 -> 2), then (cd SRC && python3 -I tools/die_plan/gen.py latency PLAN --inplace) gives lat 5 -> 6. Keep u_epc lib = signed f663e343abd8 / ff 1016d15ff88c.
- Prep gotchas: src trees lack tools/die_plan/count_frame.py (copy from head-bind-1/tools_ovl/tools/die_plan/); remap14.py/prep21z14.sh hardcode the c327 tree (see head-epc-rtl-1/prepB_run.sh, remapB.py).
- Proof: iverilog gold vs slice, hd lane pair, 30k cycles x 2 sides x clean/impaired: delivered streams identical (0 mismatches on common prefix), 0 data/credit errors, no faults. head-epc-rtl-1/simkit.
- Bind+LATCHECK on rp21z16eB (bindrun/B1): bind PASS; coll_HOST1_d PASS (table 6, delivered 4). 34 PLAN_STATIONS_UNPRICED + cohort FAIL = old rp21z16e base / single-type prep, not form B.
- Build: kit epyc7 (and intel1/epyc2/epyc8/epyc9/epyc10) head-epc-rtl-1/kitsB/g_hd_host_e/hd_host_e, ot-run log intel2 ~/tmp/hepc_build.log. Result line follows in COORD-REVIEW-QUEUE.md.
