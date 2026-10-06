# Read-only inventory of an already loaded mapped R5a ODB and its actual SDC.
# Invoke after reading the matching corner Liberty; no clock/IO edits or STA verdict.
# Rows are hex-encoded TSV so escaped hierarchy and bus names remain literal.
set r5a_file [open $::env(OT_R5A_INVENTORY_ROWS) {WRONLY CREAT EXCL}]
proc r5a_row {kind args} {
  global r5a_file
  puts $r5a_file [join [lmap x [list $kind {*}$args] {
    binary encode hex [encoding convertto utf-8 $x]
  }] "\t"]
}
set r5a_block [ord::get_db_block]
r5a_row db_units_per_micron [$r5a_block getDbUnitsPerMicron]
set r5a_counts [dict create]
set r5a_masters [dict create]
foreach inst [$r5a_block getInsts] {
  set master [$inst getMaster]
  dict incr r5a_counts [$master getName]
  dict set r5a_masters [$master getName] $master
}
dict for {name count} $r5a_counts {
  set master [dict get $r5a_masters $name]
  r5a_row master $name $count [$master getType] [$master getWidth] [$master getHeight]
}
foreach term [$r5a_block getBTerms] {
  r5a_row port [$term getName] [$term getIoType]
  if {[$term getIoType] ne "INPUT"} {continue}
  set net [$term getNet]
  if {$net eq "NULL"} {error "unconnected actual input [$term getName]"}
  foreach sink [$net getITerms] {
    set pin [$sink getMTerm]
    if {[$pin getIoType] ne "INPUT"} {continue}
    set inst [$sink getInst]
    r5a_row input_sink [$term getName] [$inst getName] [[$inst getMaster] getName] [$pin getName] [$net getName]
  }
}
set r5a_clock_nets [dict create]
set r5a_seen_clocks [dict create]
# Memory Liberty has real clock-to-read-output arcs; explicitly include its
# named clk pin even when a frontend omits it from all_registers.
foreach pin [concat [all_registers -clock_pins] [get_pins -quiet -hierarchical */clk]] {
  set name [get_full_name $pin]
  if {[dict exists $r5a_seen_clocks $name]} {continue}
  dict set r5a_seen_clocks $name 1
  set inst [$r5a_block findInst [join [lrange [split $name /] 0 end-1] /]]
  if {$inst eq "NULL"} {error "clock instance absent from ODB: $name"}
  set iterm [$inst findITerm [lindex [split $name /] end]]
  if {$iterm eq "NULL"} {error "clock sink absent from ODB: $name"}
  set inst [$iterm getInst]
  set net [$iterm getNet]
  if {$net eq "NULL"} {error "unconnected actual clock sink: $name"}
  dict set r5a_clock_nets [$net getName] $net
  set clocks [lsort -unique [lmap c [get_property $pin clocks] {get_full_name $c}]]
  r5a_row clock_sink $name [[$inst getMaster] getName] [[$iterm getMTerm] getName] [$net getName] [join $clocks ,]
  foreach output [$inst getITerms] {
    if {[[$output getMTerm] getIoType] eq "OUTPUT"} {
      set qnet [$output getNet]
      if {$qnet ne "NULL"} {
        r5a_row capture_output [$inst getName] [[$output getMTerm] getName] [$qnet getName]
      }
    }
  }
}
dict for {name net} $r5a_clock_nets {
  foreach term [$net getBTerms] {r5a_row clock_root $name [$term getName]}
  foreach term [$net getITerms] {
    if {[[$term getMTerm] getIoType] ne "OUTPUT"} {continue}
    set inst [$term getInst]
    r5a_row clock_driver $name [$inst getName] [[$inst getMaster] getName] [[$term getMTerm] getName]
  }
}
close $r5a_file
