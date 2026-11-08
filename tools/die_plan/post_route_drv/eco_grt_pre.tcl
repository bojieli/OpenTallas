# PRD seeds may already carry detailed clock/signal wires. FlexPA rejects any
# attached dbWire (DRT-0415), even though the repair must preserve that wire.
# Detach the original objects only while pin_access runs; restore on success
# and error. The normal PRD clock lock and clock geometry check are unchanged.
if {[info exists ::env(OT_ECO_GRT_PRE_CHAIN)] && $::env(OT_ECO_GRT_PRE_CHAIN) ne ""} {
  if {$::env(OT_ECO_GRT_PRE_CHAIN) eq "/work/eco_grt_pre.tcl"} {
    error "OT_PRD_PIN_ACCESS recursive pre-global-route chain"
  }
  source $::env(OT_ECO_GRT_PRE_CHAIN)
}
if {![llength [info commands ::ot_prd_pin_access_original]]} {
  rename ::pin_access ::ot_prd_pin_access_original
  proc ::pin_access {args} {
    set parked {}
    set block [::ord::get_db_block]
    try {
      foreach net [$block getNets] {
        if {[$net getSigType] in {POWER GROUND}} continue
        set wire [$net getWire]
        if {$wire eq "NULL" || $wire eq ""} continue
        lappend parked [list $net $wire]
        $wire detach
      }
      puts "OT_PRD_PIN_ACCESS parked [llength $parked] existing wires; pin checking unchanged"
      return [uplevel 1 [list ::ot_prd_pin_access_original {*}$args]]
    } finally {
      set bad {}
      set transient 0
      foreach pair $parked {
        lassign $pair net wire
        set current [$net getWire]
        if {$current eq $wire} { continue }
        if {$current ne "NULL" && $current ne ""} {
          # FlexPA may create temporary route objects while assigning access.
          # Restore the original route, not the temporary access geometry.
          incr transient
          ::odb::dbWire_destroy $current
        }
        $wire attach $net
        if {[$net getWire] ne $wire} { lappend bad [$net getName] }
      }
      puts "OT_PRD_PIN_ACCESS restored [llength $parked] original wire objects; removed $transient transient pin-access wires"
      if {[llength $bad]} {
        error "OT_PRD_PIN_ACCESS failed to restore wire objects: [lrange $bad 0 9]"
      }
    }
  }
}
