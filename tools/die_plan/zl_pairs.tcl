# LOCKUP-STATION-1130: zero-logic register pairs (Q -> only BUF/INV/HB -> D) by launch / capture tap, static (no STA)
read_db $::env(ODB)
set blk [ord::get_db_block]
set out [open $::env(OUT) w]
proc is_reg {m} { return [regexp {^(DFF|ASYNC_DFF|SDF|DHL|DLL)} $m] }
proc is_buf {m} { return [regexp {^(BUF|HB|INV|CKINV|CKBUF)} $m] }
set tapc [dict create]
proc tap_of {net} {
  global tapc
  set chain {}; set r "?"
  for {set i 0} {$i < 64} {incr i} {
    if {$net eq "NULL"} break
    set nn [$net getName]
    if {[dict exists $tapc $nn]} { set r [dict get $tapc $nn]; break }
    lappend chain $nn
    if {[regexp {^clk(_[tc][0-9]+)?$} $nn]} { set r $nn; break }
    set bts [$net getBTerms]
    if {[llength $bts]} { set r [[lindex $bts 0] getName]; break }
    set drv ""
    foreach t [$net getITerms] { if {[$t isOutputSignal]} { set drv $t; break } }
    if {$drv eq ""} break
    set net "NULL"
    foreach t [[$drv getInst] getITerms] { if {[$t isInputSignal] && [$t getNet] ne "NULL"} { set net [$t getNet]; break } }
  }
  foreach c $chain { dict set tapc $c $r }
  return $r
}
set n 0
foreach inst [$blk getInsts] {
  set m [[$inst getMaster] getName]
  if {![is_reg $m]} continue
  set ck ""; set d ""
  foreach t [$inst getITerms] {
    set nm [[$t getMTerm] getName]
    if {[$t getNet] eq "NULL"} continue
    if {[[$t getNet] getSigType] eq "CLOCK" || [regexp {^(CLK|CK|clk)$} $nm]} { set ck $t } elseif {[regexp {^(D|d)$} $nm]} { set d $t }
  }
  if {$ck eq "" || $d eq ""} continue
  set ctap [tap_of [$ck getNet]]
  # walk D back through buffers
  set net [$d getNet]; set hops 0; set src ""
  while {$hops < 40} {
    set drv ""
    foreach t [$net getITerms] { if {[$t isOutputSignal]} { set drv $t; break } }
    if {$drv eq ""} { if {[llength [$net getBTerms]]} { set src "PORT:[[lindex [$net getBTerms] 0] getName]" }; break }
    set di [$drv getInst]; set dm [[$di getMaster] getName]
    if {[is_reg $dm]} { set src $di; break }
    if {![is_buf $dm]} { set src "LOGIC"; break }
    set nn "NULL"
    foreach t [$di getITerms] { if {[$t isInputSignal] && [$t getNet] ne "NULL" && [[$t getNet] getSigType] ne "POWER" && [[$t getNet] getSigType] ne "GROUND"} { set nn [$t getNet]; break } }
    if {$nn eq "NULL"} break
    set net $nn; incr hops
  }
  if {$src eq "" || $src eq "LOGIC"} continue
  if {[string match PORT:* $src]} { continue }
  set ltap "?"
  foreach t [$src getITerms] { if {[$t getNet] ne "NULL" && ([[$t getNet] getSigType] eq "CLOCK" || [regexp {^(CLK|CK|clk)$} [[$t getMTerm] getName]])} { set ltap [tap_of [$t getNet]]; break } }
  set a [$src getLocation]; set b [$inst getLocation]
  set dist [expr {(abs([lindex $a 0]-[lindex $b 0]) + abs([lindex $a 1]-[lindex $b 1]))/double([$blk getDbUnitsPerMicron])}]
  puts $out "[$src getName]\t[$inst getName]\t$ltap\t$ctap\t$dist\t[[$src getMaster] getName]\t$m"
  incr n
}
close $out
puts "ZL_PAIRS $n"
