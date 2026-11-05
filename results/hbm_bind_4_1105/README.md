# HBM-BIND-4 11-05: d44v strict bind against the tip plan

Plan: main e891fa51a5, die_plan inner sha be781c75. Netlist: frozen 11-01 elaboration (sha ce2560d3), not a re-elaboration.
Result: 48 errors, all UNPLANNED, unbound 42,407 b, tied/undriven/multi 0 (u_table_tip.json).

Why the frozen netlist stands in for the tip here: `bind.py elab` on the tip with asbuilt_delta.json returns RC 0, but its JSON has no
post-elab transforms (dead scorer index DCE, memory_map of g_inj.slot, splice_qhub, splice_coll, fused_lower_tree_splice). cmp2.py finds
differences only in the modules those transforms touch. Of 22 source files the frozen JSON names, 17 hash equal to the tip; 5 differ:
qcen and qhub (SFR/SXC, default 0), keybuf_sliced_np4 (RS passthrough), quarter_with_keybuf_sliced (RS 1), chunk_rt_h (RST_LOCAL default 0, seed line).
The transforms were not re-run on the tip elaboration, so no plan-of-record claim rests on this.

asbuilt_delta.json applies to the scratch manifest (d44v asbuilt is not on main): 67 sub_core_leaf entries, add_lat prefer, regenerated `_s`.
