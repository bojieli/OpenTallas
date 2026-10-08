proc normal_name {n} {return [string map [list "\\" "" "/" "."] $n]}
set block [ord::get_db_block]
set sta_cells {}
foreach c [get_cells -hierarchical *] {
 set key [normal_name [get_full_name $c]]
 if {[regexp {^s[01]\..*\.(ab|ba)\.inv[01]\.} $key]} {
  puts "STA_INV raw=[get_full_name $c] normalized=$key"
  dict lappend sta_cells $key $c
 }
}
set clocks {}
foreach i [$block getInsts] {
 set key [normal_name [$i getName]]
 if {[regexp {^s[01]\..*\.(ab|ba)\.inv[01]\.} $key]} {
  if {![dict exists $sta_cells $key]} {error "Missing STA handle for [$i getName] normalized=$key"}
  set candidates [dict get $sta_cells $key]
  if {[llength $candidates]!=1} {error "Ambiguous STA handle $key"}
  if {![string match INV* [[$i getMaster] getName]]} {error "Not an inverter"}
  lappend clocks [lindex $candidates 0]
  puts "ODB_INV raw=[$i getName] normalized=$key master=[[$i getMaster] getName]"
 }
}
if {[llength $clocks]!=8} {error "expected eight mapped clock inverter cells"}
set_dont_touch $clocks
puts "TMR_ACTUAL_ODB_CLOCK_RESOLVER_PASS count=8"
