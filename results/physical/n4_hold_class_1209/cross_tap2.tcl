proc ntap {inst} {
 set it [$inst findITerm CLK]
 if {$it eq "NULL" || $it eq ""} {return NOCLK}
 set net [$it getNet];set seen [dict create]
 for {set dep 0} {$dep<100} {incr dep} {
  if {$net eq "NULL" || $net eq "" || [dict exists $seen [$net getName]]} {return UNKNOWN}
  set name [$net getName];dict set seen $name 1
  if {[regexp {ot_dtap_net_([0-9]+)} $name -> tap]} {return $tap}
  if {[llength [$net getBTerms]]} {return ROOT}
  set ds {};foreach q [$net getITerms] {if {[[$q getMTerm] getIoType] eq "OUTPUT"} {lappend ds $q}}
  if {[llength $ds]!=1} {return MULTI}
  set i [[lindex $ds 0] getInst];set ins {}
  if {![regexp {^(BUF|INV|CKINV|HB)} [[$i getMaster] getName]]} {return NONBUF}
  foreach q [$i getITerms] {if {[[$q getMTerm] getIoType] eq "INPUT" && [[$q getMTerm] getSigType] ne "POWER" && [[$q getMTerm] getSigType] ne "GROUND"} {lappend ins $q}}
  if {[llength $ins]!=1} {return FANIN}
  set net [[lindex $ins 0] getNet]
 }
 return DEEP
}
set blk [ord::get_db_block];set mp [dict create]
foreach i [$blk getInsts] {dict set mp [string map {\\ {}} [$i getName]] $i}
set f [open /out/eligible.tsv r];set out [open /out/cross_tap.tsv w];set eligible [dict create];set total 0;set cross 0
foreach row [split [string trim [read $f]] "\n"] {
 set a [split $row "\t"];lassign $a sn dn sl
 if {![dict exists $mp $sn] || ![dict exists $mp $dn]} {error "missing actual $sn $dn"}
 set si [dict get $mp $sn];set di [dict get $mp $dn];set st [ntap $si];set dt [ntap $di]
 set iscross [expr {$st ne $dt && [string is integer $st] && [string is integer $dt]}]
 puts $out "$row\t$st\t$dt\t$iscross"
 dict set eligible $dn [list $sn $iscross]
 incr total;if {$iscross} {incr cross}
}
close $f;close $out
set out [open /out/violators.tsv w];set n 0;set covered 0;set xcovered 0
foreach p [find_timing_paths -path_delay min -group_path_count 100000 -endpoint_path_count 1 -slack_max 0] {
 if {[get_property $p slack]>=0} continue
 set s [get_property $p startpoint];set e [get_property $p endpoint]
 if {[$s is_top_level_port] || [$e is_top_level_port]} continue
 set sit [sta::sta_to_db_pin $s];set dit [sta::sta_to_db_pin $e]
 if {$sit eq "NULL" || $dit eq "NULL"} {error "missing actual STA toDB pin"}
 set si [$sit getInst];set di [$dit getInst]
 set sn [string map {\\ {}} [$si getName]];set dn [string map {\\ {}} [$di getName]]
 set st [ntap $si];set dt [ntap $di];set cov 0;set xc 0
 if {[dict exists $eligible $dn]} {lassign [dict get $eligible $dn] oldsn xc;if {$oldsn eq $sn} {set cov 1;incr covered;if {$xc} {incr xcovered}}}
 puts $out "$sn\t$dn\t[get_property $p slack]\t$st\t$dt\t$cov\t$xc"
 incr n
}
close $out
puts "N4_CROSS_TAP eligible$total cross$cross FFviolators$n eligiblecovered$covered crosscovered$xcovered"
exit
