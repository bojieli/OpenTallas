set base [lindex [glob /work/results/asap7/*/base] 0]
set plat /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $plat/lef/asap7_tech_1x_201209.lef
read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob $plat/lib/NLDM/*RVT_FF*] { catch {read_liberty $f} }
read_db $base/4_1_cts.odb
proc fam {n} { regsub -all {\\} $n {} n; regsub -all {\[[0-9]+\]} $n {[]} n; regsub {\$_[A-Z0-9_]+_$} $n {} n; return $n }
set block [ord::get_db_block]
set nb 0; set famc [dict create]
foreach i [$block getInsts] {
  if {![string match hold* [$i getName]]} continue
  incr nb
  set front {}; foreach t [$i getITerms] { if {[$t isOutputSignal] && [$t getNet] ne "NULL"} { lappend front [$t getNet] } }
  set seen [dict create]; set sinks [dict create]; set steps 0
  while {[llength $front] && $steps < 400} {
    set n [lindex $front 0]; set front [lrange $front 1 end]; incr steps
    if {[dict exists $seen [$n getName]]} continue; dict set seen [$n getName] 1
    foreach t [$n getITerms] {
      if {![$t isInputSignal]} continue
      set ii [$t getInst]; set m [$ii getMaster]
      if {[$m isSequential]} { dict set sinks [fam [$ii getName]] 1 } else {
        foreach t2 [$ii getITerms] { if {[$t2 isOutputSignal] && [$t2 getNet] ne "NULL"} { lappend front [$t2 getNet] } } }
    }
    foreach b [$n getBTerms] { dict set sinks "port:[fam [$b getName]]" 1 }
  }
  set k [join [lsort [dict keys $sinks]] " + "]
  if {[dict size $sinks] > 3} { set k "MULTI([dict size $sinks]) [lindex [lsort [dict keys $sinks]] 0]" }
  dict incr famc $k
}
puts "HB total $nb"
foreach {k v} [lsort -stride 2 -index 1 -integer -decreasing [dict get $famc]] { puts "HB $v $k" }
