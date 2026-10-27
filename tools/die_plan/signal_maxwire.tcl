# Shared signal-wire segmentation at POST_RESIZE (OWNER 2026-10-27).
# Dense HBM collar: GRT estimated 197-261ps on 180um/12-load cd[*] nets,
# routed RCX measured 324-369ps because detailed routing added via resistance.
# A placement-stage 60um repair closed the successor at 0 routed slew violations.
# repair_design operates on signal nets; CTS runs later and clock nets are skipped.
estimate_parasitics -placement
set ot_sigwire_before [sta::network_leaf_instance_count]
set ot_sigwire_args [list -max_wire_length 60]
foreach {envvar flag} {SLEW_MARGIN -slew_margin CAP_MARGIN -cap_margin} {
  if {[info exists ::env($envvar)] && $::env($envvar) ne ""} {
    lappend ot_sigwire_args $flag $::env($envvar)
  }
}
repair_design {*}$ot_sigwire_args
source /work/pg_connect.tcl
ot_pg_connect_all signal_maxwire
ot_pg_require_bound signal_maxwire
estimate_parasitics -placement
puts "OT_SIGNAL_MAXWIRE 60um instances $ot_sigwire_before -> [sta::network_leaf_instance_count]"
