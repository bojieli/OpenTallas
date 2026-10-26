# Source after canonical clock_spine.tcl and the exact mapped root map.
# POST_SYNTH protects the two RTL root cells through ORFS buffer removal.
# The parent spine must reconnect their A pins, which OpenDB forbids while
# the cells are protected. Release precisely those two cells for construction
# only, then restore their original protection even when construction fails.
if {[llength [info procs ot_clock_spines]] != 1 || [llength [info procs tx_clock_spines_protected_orig]]} {
  error "TX_ROOT_PRESERVE: missing builder or duplicate lifecycle hook"
}
rename ot_clock_spines tx_clock_spines_protected_orig
proc ot_clock_spines {} {
  if {![info exists ::ot_sp_internal_roots] || [lsort [dict keys $::ot_sp_internal_roots]] ne {ga gb}} {
    error "TX_ROOT_PRESERVE: requires exact ga/gb root map"
  }
  set block [ord::get_db_block]
  set targets {}
  dict for {region row} $::ot_sp_internal_roots {
    set net [lindex [ot_sp_internal_root $region $row] 0]
    set pin [$block findITerm [lindex $row 0]]
    set inst [$pin getInst]
    set name [$inst getName]
    if {$name in $targets} {error "TX_ROOT_PRESERVE: duplicate source cell $name"}
    if {![$inst isDoNotTouch]} {error "TX_ROOT_PRESERVE: POST_SYNTH protection missing $name"}
    if {[$net isDoNotTouch]} {error "TX_ROOT_PRESERVE: output net protected before construction $name"}
    lappend targets $name
  }
  foreach name $targets {[$block findInst $name] setDoNotTouch 0}
  try {
    return [tx_clock_spines_protected_orig]
  } finally {
    foreach name $targets {
      set inst [$block findInst $name]
      if {$inst eq "NULL" || $inst eq ""} {error "TX_ROOT_PRESERVE: source cell disappeared $name"}
      $inst setDoNotTouch 1
    }
    puts "TX_ROOT_PRESERVE restored exact [llength $targets] source cells"
  }
}
