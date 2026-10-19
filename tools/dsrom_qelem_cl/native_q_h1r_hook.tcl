# native_q_h1_hook.tcl for the RSTP = 1 q element (QXPQ-RST 2026-10-17): reads native_q_h1r_input.sdc (rst_n as data).
# Source after link_budget_hook.tcl in PRE_CTS_TCL. The measured virtual
# reference is created by that hook only after clock_tree_synthesis returns.
# Apply H1 then, before CTS repair; reading the SDC directly in PRE_CTS fails.
if {[info procs clock_tree_synthesis] eq ""} {
  error "Native Q H1 hook requires clock_tree_synthesis"
}
if {[info procs ot_native_q_h1r_cts_orig] eq ""} {
  rename clock_tree_synthesis ot_native_q_h1r_cts_orig
  proc clock_tree_synthesis {args} {
    ot_native_q_h1r_cts_orig {*}$args
    read_sdc /src/tools/dsrom_qelem_cl/native_q_h1r_input.sdc
  }
}
