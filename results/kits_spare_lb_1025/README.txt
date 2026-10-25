KITS-SPARE/LB 2026-10-25 (Claude). Successor kits for S81 split cores ot_s81sl_ve_s / ot_s81sl_ve_m (kits epyc1:/srv/opentallas-scratch2/claude/kits-spare/lb/<module>_<pins sha12>)
and the cfg7bfp c2 input-seam hold probe (PROPOSAL IO-HOLD-2 in coord lanes/COORD-REVIEW-QUEUE.md).
Kit = FLOW rebuild kit (RTL claude/s81-rtlsplit-1024r split cores, leafplan r9 pin tables == main) + origin/main 0372e55a45 tools/die_plan copies
(cts_post, tap_balance, leaf_affinity, vclk_corner, postcts_gate, hold_gate, setRC_rcx_asap7 -> setRC_rcx.tcl, signoff, sdc_lint, rtl_lint, reg_fanout_gate)
+ tools/rst_entry.tcl (sourced by face_flops.tcl: u_rst sync_q FIRM at the rst_n pin) + tools/run_lb.sh (runner).
tools/postcts.sh + ck_dump.tcl + render.py = read-only post-CTS review (CK arrival per corner, hold census, density, pin->reg).
10-25 09:10 FINDING: estimate_parasitics before set_propagated_clock leaves CLOCK nets without wire RC (tools/order_check.tcl:
ve_m mul.wp[83] CK 193.2 ps est-then-propagate vs 316.5 propagate-then-estimate = the CTS report value). main tools/die_plan/postcts_gate.tcl
has that order (estimate l.38-41, propagate l.43) -> its pin-reg clock reads ~20-120 ps early; the kit copies here (tools/postcts_gate_kit.tcl)
propagate first. ck_dump.tcl / probe.tcl fixed the same way; cfg7bfp TSVs are the corrected rerun (old c2 render deleted, was wrong).
