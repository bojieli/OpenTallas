# NOT INVOKED. Exact isolated clone only after run.sh validates ROOT_APPROVAL.json.
if {![info exists ::env(INT8_EXACT_ECO_AUTHORIZED)] || $::env(INT8_EXACT_ECO_AUTHORIZED) ne "INT8_CLONE_ECO_FEB988_V1"} {error MISSING_EXACT_ECO_GRANT}
source /kit/libs_TT.tcl
read_db /baseline/output/cts_checkpoint.odb
source $p/setRC.tcl
source /kit/constraints.sdc
source /kit/vendor/native_pg_binding.tcl
set b [ord::get_db_block]
set mapping [ot_pg_prepare $b]
ot_pg_assert_all_native $b $mapping
set old_count [llength [$b getInsts]]
set old_identity [dict create]
foreach i [$b getInsts] {
 dict set old_identity [$i getName] [list [[$i getMaster] getName] [$i getLocation] [$i getOrient]]
}
set old_nets [dict create]
foreach net [$b getNets] {dict set old_nets [$net getId] [list [$net getName] [$net getSigType] [$net isDoNotTouch]]}
set changed {};set added {};set new_nets {};set touched {}
proc eco_master {n} {
 set m [[ord::get_db] findMaster $n]
 if {$m eq "NULL"} {error "UNKNOWN_MASTER $n"};return $m
}
proc eco_inst {n} {
 set i [$::b findInst $n];if {$i eq "NULL"} {error "MISSING_INSTANCE $n"};return $i
}
proc eco_replace {n old new} {
 set i [eco_inst $n]
 if {[[$i getMaster] getName] ne $old || [$i isDoNotTouch]} {error "REPLACE_IDENTITY_OR_PROTECTION $n"}
 if {![$i swapMaster [eco_master $new]]} {error "REPLACE_FAILED $n"}
 set ::mapping [ot_pg_prepare $::b]
 ot_pg_bind_before_protect $::mapping $i
 dict set ::changed $n 1
}
proc eco_add {n master} {
 if {[$::b findInst $n] ne "NULL"} {error "DUPLICATE_INSTANCE $n"}
 set i [odb::dbInst_create $::b [eco_master $master] $n]
 if {$i eq "NULL"} {error "CREATE_FAILED $n"}
 # Native master PG MTerms bind immediately, before signal wires/protection.
 set ::mapping [ot_pg_prepare $::b]
 ot_pg_bind_before_protect $::mapping $i
 dict set ::added $n 1
}
proc eco_net {n} {
 if {[$::b findNet $n] ne "NULL"} {error "DUPLICATE_NET $n"}
 set net [odb::dbNet_create $::b $n];$net setSigType SIGNAL
 dict set ::new_nets $n 1
}
proc eco_connect {n pin original target} {
 set i [eco_inst $n];set t [$i findITerm $pin]
 if {$t eq "NULL" || [$t getSigType] in {POWER GROUND CLOCK}} {error "ILLEGAL_SIGNAL_PIN $n/$pin"}
 set net [$t getNet];set actual "";if {$net ne "NULL"} {set actual [$net getName]}
 if {$actual ne $original} {error "ORIGINAL_NET_MISMATCH $n/$pin expected=$original actual=$actual"}
 set targetnet [$::b findNet $target];if {$targetnet eq "NULL" || [$targetnet getSigType] ne "SIGNAL"} {error "BAD_TARGET_NET $target"}
 set key [list $n $pin];if {[dict exists $::touched $key]} {error DUPLICATE_REWIRE}
 $t disconnect;$t connect $targetnet;dict set ::touched $key 1
}
proc eco_place {n x y} {
 set i [eco_inst $n];set match {}
 foreach row [$::b getRows] {
  set box [$row getBBox]
  if {[$box yMin]==$y && [$box xMin]<=$x && [$box xMax]>=$x} {lappend match $row}
 }
 if {[llength $match]!=1} {error "AMBIGUOUS_NATIVE_ROW $n $x $y"}
 set row [lindex $match 0];$i setOrient [$row getOrient];$i setLocation $x $y;$i setPlacementStatus PLACED
}
source /kit/exact_changes.tcl
if {[dict size $changed]!=1078 || [dict size $added]!=1866 || [dict size $new_nets]!=1866 || [dict size $touched]!=4414} {error EXACT_SCOPE_MISMATCH}
if {[llength [$b getInsts]]!=$old_count+1866} {error INSTANCE_CARDINALITY}
foreach i [$b getInsts] {
 set n [$i getName]
 if {[dict exists $old_identity $n] && ![dict exists $changed $n]} {
  if {[dict get $old_identity $n] ne [list [[$i getMaster] getName] [$i getLocation] [$i getOrient]]} {error "IMMUTABLE_INSTANCE_CHANGED $n"}
 }
}
foreach net [$b getNets] {
 if {[dict exists $old_nets [$net getId]] && [dict get $old_nets [$net getId]] ne [list [$net getName] [$net getSigType] [$net isDoNotTouch]]} {error "ORIGINAL_NET_METADATA_CHANGED [$net getName]"}
}
if {[llength [all_registers]]!=2782} {error FF_IDENTITY_COUNT}
check_placement -verbose
set mapping [ot_pg_prepare $b]
set pg [ot_pg_assert_all_native $b $mapping]
if {$pg!=24978} {error "PG_CARDINALITY $pg expected24978"}
# Full native master PG binding and legal placement checkpoint first.
# Physical conductor-contact proof and complete STA remain mandatory AFTER it.
write_db /output/eco_pg_checkpoint.odb
write_verilog /output/eco_pg_checkpoint.v
set fd [open /output/checkpoint.status w]
puts $fd "PG_BINDING_CHECKED_EXACT_CLONE_SCOPE placement_check_called=1 native_pg=$pg replacements=1078 additions=1866 NO_CTS_NO_ROUTE_NO_ADOPTION"
close $fd
puts "INT8_CLONE_ECO_CHECKPOINT_SAVED NO_CTS_NO_ROUTE"
