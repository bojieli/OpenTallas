# Kant corrected provisional four-square allocation. Geometry only; no SDC edits.
# Bind existing CRC state and its actual exclusive combinational fanin. Shared
# controller/CDC logic stays in the central facade area, never counted twice.
set lc_block [ord::get_db_block]
set lc_dbu [$lc_block getDbUnitsPerMicron]
proc lc_fanin {registers} {
  set queue {}; set nets [dict create]; set cells [dict create]
  foreach inst $registers {
    foreach it [$inst getITerms] {
      if {[[$it getMTerm] getName] eq "D" && [$it getNet] ne "NULL"} {
        lappend queue [$it getNet]
      }
    }
  }
  while {[llength $queue]} {
    set net [lindex $queue end]; set queue [lrange $queue 0 end-1]
    if {[dict exists $nets [$net getName]]} {continue}
    dict set nets [$net getName] 1
    foreach it [$net getITerms] {
      if {![$it isOutputSignal]} {continue}
      set inst [$it getInst]; set name [$inst getName]
      if {[[$inst getMaster] isSequential] || [dict exists $cells $name]} {continue}
      dict set cells $name $inst
      foreach input [$inst getITerms] {
        if {[$input isInputSignal] && [$input getNet] ne "NULL"} {
          lappend queue [$input getNet]
        }
      }
    }
  }
  return $cells
}
set lc_specs {
  {load_host {g_on.g_die[0].u_load.g_on.crc_got[} 8.64 298.944 273.024 563.328}
  {store_host {g_on.g_die[0].u_store.g_on.crc_got[} 298.944 298.944 563.328 563.328}
  {load_mem {g_on.g_die[0].u_load.g_on.vcrc[} 8.64 8.64 273.024 273.024}
  {store_mem {g_on.g_die[0].u_store.g_on.mcrc[} 298.944 8.64 563.328 273.024}
}
set lc_registers [dict create]; set lc_cones [dict create]; set lc_owners [dict create]
foreach spec $lc_specs {
  lassign $spec name prefix x0 y0 x1 y1
  set registers {}
  foreach inst [$lc_block getInsts] {
    # OpenDB stores Yosys bus names with escaped brackets. Normalize only
    # their representation; retain the complete die/engine/state identity.
    set actual_name [string map [list "\\" ""] [$inst getName]]
    if {[string first $prefix $actual_name] == 0 && [[$inst getMaster] isSequential]} {
      lappend registers $inst
    }
  }
  if {[llength $registers] != 32} {error "CRC slot $name state census !=32"}
  dict set lc_registers $name $registers
  set cone [lc_fanin $registers]; dict set lc_cones $name $cone
  dict for {cell inst} $cone {dict lappend lc_owners $cell $name}
}
foreach spec $lc_specs {
  lassign $spec name prefix x0 y0 x1 y1
  set region [odb::dbRegion_create $lc_block "loader_crc_$name"]
  # OpenDB EXCLUSIVE is the DEF FENCE region type.
  $region setRegionType EXCLUSIVE
  odb::dbBox_create $region [expr {round($x0*$lc_dbu)}] [expr {round($y0*$lc_dbu)}] [expr {round($x1*$lc_dbu)}] [expr {round($y1*$lc_dbu)}]
  set group [odb::dbGroup_create $region "loader_crc_$name"]
  foreach inst [dict get $lc_registers $name] {$group addInst $inst}
  set exclusive 0; set shared 0
  dict for {cell inst} [dict get $lc_cones $name] {
    if {[llength [dict get $lc_owners $cell]] == 1} {
      $group addInst $inst; incr exclusive
    } else {incr shared}
  }
  if {$exclusive == 0} {error "CRC slot $name has no actual exclusive mapped cone"}
  puts "LOADER_CRC_REGION $name state32 exclusive_comb=$exclusive shared_control=$shared box=$x0,$y0,$x1,$y1"
}
