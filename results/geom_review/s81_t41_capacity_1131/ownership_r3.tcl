read_db /work/run/results/asap7/dp_slice_station__t41/base/3_place.odb
set blk [ord::get_db_block]
set u [[ord::get_db_tech] getDbUnitsPerMicron]
proc geometry_snapshot {} {
 set rows {}
 foreach i [[ord::get_db_block] getInsts] {dict set rows [$i getName] [list [[$i getMaster] getName] [$i getLocation] [$i getOrient] [$i getPlacementStatus]]}
 return $rows
}
proc forwarded_snapshot {} {
 set rows {}
 foreach bt [[ord::get_db_block] getBTerms] {
  if {![regexp {^fclk_in} [$bt getName]]} continue
  set ns {};foreach it [[$bt getNet] getITerms] {lappend ns [$it getName]}
  dict set rows [$bt getName] [lsort $ns]
 }
 return $rows
}
set geo [geometry_snapshot]
set ef [open /work/landing_exports.tcl];set export_text [read $ef];close $ef
set expected_exports [regexp -all -inline {set cland_dst \[\$cland_block findBTerm \{([^\}]+)\}\]\nset cland_src \[\$cland_block findBTerm \{([^\}]+)\}\]} $export_text]
set old_forwarders {}
foreach {whole dst src} $expected_exports {
 set oldnet [[$blk findBTerm $dst] getNet];set seen {}
 while {$oldnet ne "NULL" && $oldnet ne "" && ![dict exists $seen [$oldnet getName]]} {
  dict set seen [$oldnet getName] 1
  set drivers {};foreach it [$oldnet getITerms] {if {[$it isOutputSignal]} {lappend drivers $it}}
  if {[llength $drivers]!=1} break
  set i [[lindex $drivers 0] getInst]
  if {![string match BUF* [[$i getMaster] getName]]} break
  dict set old_forwarders [$i getName] 1
  set up "NULL";foreach it [$i getITerms] {if {[$it isInputSignal]} {set up [$it getNet]}}
  set oldnet $up
 }
}
set fwd [forwarded_snapshot]
set touched {};foreach bt [$blk getBTerms] {
 if {![regexp {^clk(_t[0-9]+)?$} [$bt getName]]} continue
 foreach it [[$bt getNet] getITerms] {if {[[$it getMTerm] getIoType] eq "INPUT"} {dict set touched [$it getName] 1}}
}
set data {};foreach i [$blk getInsts] {foreach it [$i getITerms] {if {![dict exists $touched [$it getName]] && ![dict exists $old_forwarders [$i getName]]} {set n [$it getNet]; dict set data [$it getName] [expr {$n eq "NULL" || $n eq "" ? "" : [$n getName]}]}}}
source /work/clock_taps.tcl
write_db /out/post_hook.odb
set errors {};set added {};set removed {}
dict for {name row} $geo {
 set i [$blk findInst $name]
 if {$i eq "NULL" || $i eq ""} {
  lappend removed $name
  if {![dict exists $old_forwarders $name]} {lappend errors "unexpected removed instance $name"}
 } elseif {$row ne [list [[$i getMaster] getName] [$i getLocation] [$i getOrient] [$i getPlacementStatus]]} {lappend errors "old geometry changed $name"}
}
foreach i [$blk getInsts] {if {![dict exists $geo [$i getName]]} {lappend added [$i getName];if {![string match cland_fwd_fclk_out_* [$i getName]] || [[$i getMaster] getName] ne "BUFx24_ASAP7_75t_R"} {lappend errors "unexpected added clock instance [$i getName]"}}}
if {$fwd ne [forwarded_snapshot]} {lappend errors "inbound forwarded-clock ownership changed"}
foreach i [$blk getInsts] {foreach it [$i getITerms] {if {[dict exists $data [$it getName]]} {set n [$it getNet];set now [expr {$n eq "NULL" || $n eq "" ? "" : [$n getName]}];if {$now ne [dict get $data [$it getName]]} {lappend errors "non-grid connectivity changed at [$it getName]"}}}}
set out [open /out/ownership.tsv w]
puts $out "audit\terrors\t[llength $errors]\tplanned_forward_buffers_added\t[llength $added]\told_forward_buffers_removed\t[llength $removed]"
foreach e $errors {puts $out "error\t$e"}
set groups {}
foreach tp $ct_taps {
 lassign $tp name net tx ty
 set count 0;set far 0;set farname ""
 foreach it [$net getITerms] {
  if {[[$it getMTerm] getIoType] ne "INPUT"} continue
  incr count;set i [$it getInst];set bb [$i getBBox]
  set dist [expr {(abs(([$bb xMin]+[$bb xMax])/2.0-$tx)+abs(([$bb yMin]+[$bb yMax])/2.0-$ty))/$u}]
  if {$dist>$far} {set far $dist;set farname [$i getName]}
  if {[regexp {(?:^|[/.])(u_ft_[A-Za-z0-9_]+)[/.]} [$i getName] -> g]} {dict incr groups $g,$name}
 }
 puts $out "tap\t$name\t$count\t$far\t$farname"
}
dict for {name members} $fwd {puts $out "forwarded\t$name\t[llength $members]"}
dict for {g n} $groups {puts $out "ft_group_owner\t$g\t$n"}
puts $out "group_rule\t$ct_gre\tfollow_rule\t$ct_fre"
foreach {whole dst src} $expected_exports {
 set bname [regsub {\[0\]$} $dst {}];set i [$blk findInst cland_fwd_$bname]
 if {$i eq "NULL" || $i eq "" || [[$i findITerm A] getNet] ne [[$blk findBTerm $src] getNet] || [[$i findITerm Y] getNet] ne [[$blk findBTerm $dst] getNet]} {lappend errors "forwarded export mismatch $dst <- $src"}
 puts $out "export\t$dst\t$src\t[expr {$i ne "NULL" && $i ne ""}]"
}
puts $out "final_errors\t[llength $errors]"
close $out
if {[llength $errors]} {error "ownership audit failed: [lrange $errors 0 6]"}
puts "OWNERSHIP_PROBE_PASS geometry/forwarded/data unchanged; no CTS/GRT/STA"
