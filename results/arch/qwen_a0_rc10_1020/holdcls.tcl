read_db /d/4_1_cts.odb
set block [ord::get_db_block]
proc cls {n} {
  regsub -all {\\} $n {} n
  regsub -all {\[[0-9]+\]} $n {[]} n
  regsub {\$_.*} $n {} n
  regsub {^u_ot_pr_core\.u_g\.u_tile\.u_tile\.u_logic\.} $n {} n
  return $n
}
proc ishold {i} { set m [[$i getMaster] getName]; return [expr {[string match "*hold*" [$i getName]] || [string match "HB*" $m]}] }
set pairs [dict create]
set nh 0
foreach i [$block getInsts] {
  if {![string match "*hold*" [$i getName]]} continue
  incr nh
  # forward
  set cur $i; set ep "?"
  for {set k 0} {$k < 40} {incr k} {
    set on ""
    foreach it [$cur getITerms] { if {[$it isOutputSignal]} { set on [$it getNet] } }
    if {$on eq "" || $on eq "NULL"} break
    set nxt ""
    foreach it [$on getITerms] { if {[$it isInputSignal]} { set nxt [$it getInst]; break } }
    if {$nxt eq ""} { set ep "PORT"; break }
    if {[string match "*hold*" [$nxt getName]]} { set cur $nxt; continue }
    set ep [cls [$nxt getName]]; break
  }
  set cur $i; set sp "?"
  for {set k 0} {$k < 40} {incr k} {
    set inn ""
    foreach it [$cur getITerms] { if {[$it isInputSignal]} { set inn [$it getNet]; break } }
    if {$inn eq "" || $inn eq "NULL"} break
    set drv ""
    foreach it [$inn getITerms] { if {[$it isOutputSignal]} { set drv [$it getInst]; break } }
    if {$drv eq ""} { set sp "PORT"; break }
    if {[string match "*hold*" [$drv getName]] || [string match "BUF*" [[$drv getMaster] getName]]} { set cur $drv; continue }
    set sp [cls [$drv getName]]; break
  }
  dict incr pairs "$sp  ->  $ep"
}
puts "HOLDCELLS $nh"
set l {}
dict for {k v} $pairs { lappend l [list $v $k] }
foreach e [lrange [lsort -integer -decreasing -index 0 $l] 0 60] { puts "CLS [lindex $e 0] [lindex $e 1]" }
exit
