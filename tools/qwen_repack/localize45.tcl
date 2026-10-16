# Localize actual mapped FFs and their exclusive data cones, with no SDC edits.
# Fences must not be silently overfull: measure actual master area after mapping.
set q45_block [ord::get_db_block]
set q45_dbu [$q45_block getDbUnitsPerMicron]
proc q45_root {net {depth 0}} {
  if {$depth > 50} {error "Q45 clock trace exceeds50"}
  foreach bt [$net getBTerms] {
    if {[$bt getIoType] eq "INPUT"} {return [$bt getName]}
  }
  foreach it [$net getITerms] {
    if {![$it isOutputSignal]} {continue}
    set inst [$it getInst]
    set master [[$inst getMaster] getName]
    if {![regexp {^(BUF|INV|CLK)} $master]} {error "Q45 unexpected clock driver $master"}
    foreach input [$inst getITerms] {
      if {[$input isInputSignal] && [$input getNet] ne "NULL"} {
        return [q45_root [$input getNet] [expr {$depth + 1}]]
      }
    }
  }
  error "Q45 undriven clock [$net getName]"
}
proc q45_fanin {registers} {
  set queue {}; set nets [dict create]; set cells [dict create]
  foreach inst $registers {
    set d [$inst findITerm D]
    if {$d ne "NULL" && [$d getNet] ne "NULL"} {lappend queue [$d getNet]}
  }
  while {[llength $queue]} {
    set net [lindex $queue end]; set queue [lrange $queue 0 end-1]
    if {[dict exists $nets [$net getId]]} {continue}
    dict set nets [$net getId] 1
    foreach it [$net getITerms] {
      if {![$it isOutputSignal]} {continue}
      set inst [$it getInst]; set master [$inst getMaster]; set name [$inst getName]
      if {[$master isBlock] || [$master isSequential] || [dict exists $cells $name]} {continue}
      dict set cells $name $inst
      foreach input [$inst getITerms] {
        if {[$input isInputSignal] && [$input getNet] ne "NULL"} {lappend queue [$input getNet]}
      }
    }
  }
  return $cells
}
set q45_regs [dict create]; set q45_cones [dict create]; set q45_owners [dict create]
foreach inst [$q45_block getInsts] {
  set master [$inst getMaster]
  if {[$master isBlock] || ![$master isSequential]} {continue}
  set cp [$inst findITerm CLK]
  if {$cp eq "NULL" || [$cp getNet] eq "NULL"} {error "Q45 sequential cell missing clock [$inst getName]"}
  set root [q45_root [$cp getNet]]
  if {![dict exists $q45_boxes $root]} {error "Q45 unassigned mapped clock root $root"}
  dict lappend q45_regs $root $inst
}
if {[dict size $q45_regs] != 26} {error "Q45 expected26 actual soft roots"}
dict for {root registers} $q45_regs {
  if {[llength $registers] > 5000} {error "Q45 root $root exceeds structural5000sink bound"}
  set cone [q45_fanin $registers]; dict set q45_cones $root $cone
  dict for {cell inst} $cone {dict lappend q45_owners $cell $root}
}
set q45_report [open q45_actual_regions.tsv w]
puts $q45_report "root\tff_sinks\texclusive_comb\tshared_comb\tcell_area_um2\tplaceable_um2\tutilization"
dict for {root boxes} $q45_boxes {
  set region [odb::dbRegion_create $q45_block q45_$root]
  $region setRegionType EXCLUSIVE
  set capacity 0.0
  foreach box $boxes {
    lassign $box x0 y0 x1 y1
    set capacity [expr {$capacity + ($x1-$x0)*($y1-$y0)}]
    odb::dbBox_create $region [expr {round($x0*$q45_dbu)}] [expr {round($y0*$q45_dbu)}] [expr {round($x1*$q45_dbu)}] [expr {round($y1*$q45_dbu)}]
  }
  set group [odb::dbGroup_create $region q45_$root]
  set area 0.0; set exclusive 0; set shared 0
  foreach inst [dict get $q45_regs $root] {
    $group addInst $inst
    set m [$inst getMaster]
    set area [expr {$area + double([$m getWidth])*[$m getHeight]/($q45_dbu*$q45_dbu)}]
  }
  dict for {cell inst} [dict get $q45_cones $root] {
    if {[llength [dict get $q45_owners $cell]] != 1} {incr shared; continue}
    $group addInst $inst; incr exclusive
    set m [$inst getMaster]
    set area [expr {$area + double([$m getWidth])*[$m getHeight]/($q45_dbu*$q45_dbu)}]
  }
  set fill [expr {$area/$capacity}]
  puts $q45_report "$root\t[llength [dict get $q45_regs $root]]\t$exclusive\t$shared\t$area\t$capacity\t$fill"
  puts "Q45_REGION $root FF=[llength [dict get $q45_regs $root]] exclusive=$exclusive shared=$shared area=$area capacity=$capacity fill=$fill"
  if {$fill > .60} {close $q45_report; error "Q45 $root actual mapped region fill exceeds60percent; redesign required"}
}
close $q45_report
puts "Q45_LOCALIZE_PASS roots26 all_actual_mapped_FF_owned exclusive_data_cones_fenced capacity_checked"
