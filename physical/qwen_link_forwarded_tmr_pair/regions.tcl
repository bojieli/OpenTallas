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
proc qwen_fwd_normal_name {n} {return [string map [list "\\" "" "/" "."] $n]}
set sta_cells {}
foreach c [get_cells -hierarchical *] {
 set key [qwen_fwd_normal_name [get_full_name $c]]
 if {[regexp {^s[01]\..*\.(ab|ba)\.inv[01]\.} $key]} {
  puts "STA_INV raw=[get_full_name $c] normalized=$key"
  dict lappend sta_cells $key $c
 }
}
set clock_cells {}
foreach i [$block getInsts] {
 set key [qwen_fwd_normal_name [$i getName]]
 if {[regexp {^s[01]\..*\.(ab|ba)\.inv[01]\.} $key]} {
  if {![dict exists $sta_cells $key]} {error "Missing STA handle for [$i getName] normalized=$key"}
  set candidates [dict get $sta_cells $key]
  if {[llength $candidates]!=1} {error "Ambiguous STA handle $key"}
  if {![string match INV* [[$i getMaster] getName]]} {error "Not an inverter"}
  lappend clock_cells [lindex $candidates 0]
  puts "ODB_INV raw=[$i getName] normalized=$key master=[[$i getMaster] getName]"
 }
}
if {[llength $clock_cells]!=8} {error "expected eight mapped clock inverter cells"}
set_dont_touch $clock_cells
puts "TMR_ACTUAL_ODB_CLOCK_RESOLVER_PASS count=8"
