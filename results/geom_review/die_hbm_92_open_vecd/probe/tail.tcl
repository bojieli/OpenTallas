set blk [ord::get_db_block]; set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
array set root {}
proc ckroot {inst} {
  global blk root
  set i [$blk findInst $inst]
  if {$i eq "NULL"} {return "?"}
  set ck ""
  foreach it [$i getITerms] { set mt [$it getMTerm]; if {[$mt getSigType] eq "CLOCK" || [string match -nocase "CLK" [$mt getName]] || [$mt getName] eq "CK"} { set ck $it; break } }
  if {$ck eq ""} {return "?"}
  set n [$ck getNet]; set seen 0
  while {$n ne "NULL" && $seen < 60} {
    incr seen
    set key [$n getName]
    if {[info exists root($key)]} {return $root($key)}
    set bts [$n getBTerms]
    if {[llength $bts]} { set r [[lindex $bts 0] getName]; set root($key) $r; return $r }
    set drv ""
    foreach it [$n getITerms] { if {[$it isOutputSignal]} { set drv $it; break } }
    if {$drv eq ""} {return "?"}
    set di [$drv getInst]; set nn "NULL"
    foreach it [$di getITerms] { if {[$it isInputSignal] && [$it getNet] ne "NULL" && [[$it getNet] getSigType] ne "POWER" && [[$it getNet] getSigType] ne "GROUND"} { set nn [$it getNet]; break } }
    set n $nn
  }
  return "?"
}
proc loc {inst} { global blk dbu; set i [$blk findInst $inst]; if {$i eq "NULL"} {return "- -"}; set b [$i getBBox]; return "[format %.1f [expr {[$b xMin]/double($dbu)}]] [format %.1f [expr {[$b yMin]/double($dbu)}]]" }
set f [open /out/hold_paths.tsv w]
puts $f "slack\tstart\tsroot\tsx\tsy\tend\teroot\tex\tey"
set paths [find_timing_paths -path_delay min -slack_max 0 -group_path_count 20000 -endpoint_path_count 1]
foreach p $paths {
  set sp [get_full_name [get_property $p startpoint]]; set ep [get_full_name [get_property $p endpoint]]
  set sl [format %.2f [sta::time_sta_ui [get_property $p slack]]]
  set si [regsub {/[^/]+$} $sp {}]; set ei [regsub {/[^/]+$} $ep {}]
  if {$si eq $sp} {set sr PORT; set sl2 "- -"} else {set sr [ckroot $si]; set sl2 [loc $si]}
  if {$ei eq $ep} {set er PORT; set el2 "- -"} else {set er [ckroot $ei]; set el2 [loc $ei]}
  puts $f "$sl\t$sp\t$sr\t[lindex $sl2 0]\t[lindex $sl2 1]\t$ep\t$er\t[lindex $el2 0]\t[lindex $el2 1]"
}
close $f
puts "PROBE_DONE [llength $paths]"
