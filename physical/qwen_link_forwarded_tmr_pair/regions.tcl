set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
foreach {name box} {s0 {2.16 2.16 127.848 66.912} s1 {432.72 2.16 558.408 66.912}} {
 set r [odb::dbRegion_create $block "fwd_$name"]
 $r setRegionType EXCLUSIVE
 set coords {}; foreach x $box {lappend coords [expr {round($x*$dbu)}]}
 odb::dbBox_create $r {*}$coords
 set g [odb::dbGroup_create $block "fwd_$name"]
 $r addGroup $g
 set count 0
 foreach i [$block getInsts] {
  if {[string match "${name}.*" [$i getName]] || [string match "${name}/*" [$i getName]]} {$g addInst $i; incr count}
 }
 if {$count < 1068} {error "Full stage $name missing: $count cells"}
 puts "FORWARDED_REGION $name $box cells=$count"
}

# Retain the actual clock-polarity pair through physical optimization. These
# are tiny roots; CTS must buffer their loads, not collapse the pair to a wire.
set clock_cells {}
foreach i [$block getInsts] {
 set n [string map {/ .} [$i getName]]
 if {[regexp {^s[01]\..*\.(ab|ba)\.inv[01]\.} $n]} {
  if {![string match INV* [[$i getMaster] getName]]} {error "clock inverter mapped to unexpected cell"}
  foreach c [get_cells -hierarchical *] {
   if {[get_full_name $c] eq [$i getName]} {lappend clock_cells $c}
  }
 }
}
if {[llength $clock_cells] != 8} {error "expected eight real clock inverter cells: $clock_cells"}
set_dont_touch $clock_cells
