# el1011-ds-vm/be 2026-10-12: re-apply the dsfd_vm_be_sl stream-domain boundary (str_clk on cks; vrv/vrq out, rns_in in)
# AFTER the ref_tile io_ref switch, which unsets every IO delay and re-times all ports against core_clk.  Without this the
# stream ports are timed against core_clk (or not at all) from CTS to detail route and only meet str_clk at sign-off.
# Sourced via spec "boundary_tcl" (tools/ref_tile): in PRE_CTS it wraps clock_tree_synthesis (after the io_ref wrapper),
# so the str_clk delays are referenced to the PROPAGATED str_clk tree and baked into 4_cts.sdc; in PRE_GLOBAL_ROUTE and
# POST_DETAIL_ROUTE it runs directly after pre_ref_skew / post_plain.
set ::ot_besl_sdc [file join [file dirname [info script]] be_sl_clock_ref.sdc]
proc ot_besl_str_boundary {} {
  catch {estimate_parasitics -placement}
  read_sdc $::ot_besl_sdc
  puts "BE_SL str_clk boundary re-applied after io_ref switch"
}
if {[llength [info commands ::qdm_cts_orig]] && ![llength [info commands ::ot_besl_cts_inner]]} {
  rename clock_tree_synthesis ::ot_besl_cts_inner
  proc clock_tree_synthesis {args} { ::ot_besl_cts_inner {*}$args; ot_besl_str_boundary }
} else {
  ot_besl_str_boundary
}
