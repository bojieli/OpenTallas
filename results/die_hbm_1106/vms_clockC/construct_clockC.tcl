# Fresh clock construction from the immutable A CTS DB, before any data-ECO freeze.
foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT*.lib*] {
 if {![string match *FAKE* $f]} {read_liberty $f}
}
foreach f [glob /work/macros/*_tt.lib] {read_liberty $f}
set base /work/run/results/asap7/hbc_hnx_vms_bank_q0_faces__vecd4ae/base
read_db $base/4_cts.odb
read_sdc $base/4_cts.sdc
set b [ord::get_db_block]
set native_ports {clk clk_e clk_s clk_n clk_w clk_macro0 clk_macro1 clk_macro2}
set root_cache [dict create]
proc clock_root {n {depth 0}} {
 global root_cache native_ports
 if {$n eq "NULL" || $depth>128} {error "unresolved clock ancestry"}
 set key [$n getName]
 if {[dict exists $root_cache $key]} {return [dict get $root_cache $key]}
 set ports {}
 foreach p [$n getBTerms] {if {[$p getIoType] eq "INPUT"} {lappend ports [$p getName]}}
 if {[llength $ports]} {
  if {[llength $ports]!=1 || [lsearch -exact $native_ports [lindex $ports 0]]<0} {error "unknown root $ports"}
  set ans [list [lindex $ports 0] 0]
 } else {
  set drivers {}; foreach p [$n getITerms] {if {[$p isOutputSignal]} {lappend drivers $p}}
  if {[llength $drivers]!=1} {error "nonunique clock driver $key"}
  set i [[lindex $drivers 0] getInst]; set master [[$i getMaster] getName]
  if {![regexp {^(BUF|INV|CKINV|HB)} $master]} {error "non-buffer clock ancestry $key $master"}
  set inputs {}; foreach p [$i getITerms] {if {[$p isInputSignal]} {lappend inputs [$p getNet]}}
  if {[llength $inputs]!=1} {error "nonunique clock input $key"}
  set ans [clock_root [lindex $inputs 0] [expr {$depth+1}]]
  if {[regexp {^(INV|CKINV)} $master]} {lset ans 1 [expr {1^[lindex $ans 1]}]}
 }
 dict set root_cache $key $ans; return $ans
}
proc clock_membership {} {
 global b root_cache
 set root_cache [dict create]; set result [dict create]
 foreach i [$b getInsts] {
  set m [[$i getMaster] getName]
  if {![string match DFF* $m] && ![string match ot_sram* $m]} continue
  foreach p [$i getITerms] {
   set t [$p getMTerm]; set name [$t getName]
   if {[$t getSigType] ne "CLOCK" && [lsearch -exact {CLK CK clk ck} $name]<0} continue
   dict set result "[$i getName]/$name" [clock_root [$p getNet]]
  }
 }
 return $result
}
set before [clock_membership]
if {[dict size $before]<11000} {error "clock endpoint coverage too small"}
set n [$b findNet net14308]; set sink [$b findInst wire14308]; set source [$b findInst wire14309]
if {$n eq "NULL" || $sink eq "NULL" || $source eq "NULL"} {error "immutable A chain not found"}
if {[llength [$n getITerms]]!=2 || [llength [$n getBTerms]]} {error "net14308 no longer point-to-point"}
set saved_touch [$n isDoNotTouch]; $n setDoNotTouch 0
set st [$source isDoNotTouch]; set dt [$sink isDoNotTouch]
$source setDoNotTouch 0; $sink setDoNotTouch 0
# Same explicit ODB clock-construction primitives as core_density_taps.tcl.
set oldwire [$n getWire]
if {$oldwire ne "NULL"} {odb::dbWire_destroy $oldwire; puts "CLOCK_CONSTRUCTION explicitly removed only old net14308 route for this new clock baseline"}
set oldload [$sink findITerm A]
if {[$oldload getNet] ne $n} {error "unexpected original sink net"}
$oldload disconnect
set master [[ord::get_db] findMaster BUFx12f_ASAP7_75t_R]
if {$master eq "NULL"} {error "positive repeater master missing"}
set previous $n
foreach item {{0 35.64 161.73} {1 35.64 235.17} {2 35.64 307.26}} {
 lassign $item k x y
 set name codex_clk14308_c$k
 set cell [odb::dbInst_create $b $master $name]
 set nn [odb::dbNet_create $b ${name}_n]
 $nn setSigType [$n getSigType]
 [$cell findITerm A] connect $previous
 [$cell findITerm Y] connect $nn
 $cell setLocation [expr {round($x*1000)}] [expr {round($y*1000)}]
 $cell setPlacementStatus PLACED
 set previous $nn
}
$oldload connect $previous
$n setDoNotTouch $saved_touch
$source setDoNotTouch $st; $sink setDoNotTouch $dt
detailed_placement
check_placement -verbose
set after [clock_membership]
if {$before ne $after} {error "native clock endpoint root/phase membership changed"}
set f [open /work/CLOCK_CONSTRUCTION.tsv w]
puts $f "endpoint_count\t[dict size $before]"
foreach name {codex_clk14308_c0 codex_clk14308_c1 codex_clk14308_c2} {
 set i [$b findInst $name]
 puts $f "NEW\t$name\t[[$i getMaster] getName]\t[$i getLocation]"
 $i setPlacementStatus LOCKED
 $i setDoNotTouch 1
 foreach p [$i getITerms] {if {[$p isInputSignal] || [$p isOutputSignal]} {set nn [$p getNet]; if {$nn ne "NULL"} {$nn setDoNotTouch 1}}}
}
close $f
puts "CLOCK_CONSTRUCTION PASS: 3 positive buffers; [dict size $before] endpoint native roots/phases unchanged; zero pin cycles"
write_db $base/4_1_cts.odb
write_db $base/4_cts.odb
write_verilog $base/4_cts.v
exit
