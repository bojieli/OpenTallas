# Run only in a new private staged kit under ordinary admission, after source approval.
# This isolated native PA step exits before any detailed route.
foreach v {VMS_GUARD_INPUT_ODB VMS_GUARD_OUTPUT_ODB} {
  if {![info exists ::env($v)]} { error "VMS guard PA: missing $v" }
}
read_db $::env(VMS_GUARD_INPUT_ODB)
set ::env(RESULTS_DIR) [file dirname $::env(VMS_GUARD_INPUT_ODB)]
set here [file dirname [info script]]
set ::env(OT_ECO_REROUTE_DATA) 1
set ::env(OT_ECO_DRT_PRE_CHAIN) [file join $here vms_macro_west_via_guard.tcl]
# Existing released hook: guarded DATA unwire, clock comparison, full AP reset.
source [file join $here eco_drt_pre.tcl]
pin_access
write_db $::env(VMS_GUARD_OUTPUT_ODB)
puts "VMS_GUARD_PA_ONLY_DONE: inspect native FlexPA report; detailed route NOT RUN"
exit
