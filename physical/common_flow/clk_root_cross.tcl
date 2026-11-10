# CLK-ROOT-CROSS (DIE-HBM-97 11-10, COORD vecd-clkroot-gen): root repeater for a clock port boxed in by macros.
# Sourced first in the HBM generator's post_cts_setup.tcl (POST_CTS, before the kit's tap / leaf balance): dumps every
# clock port net (port location, sinks), the macro boxes, the rows and the placed instances to JSON, runs
# /work/clk_root_cross.py plan (pure geometry rule, see that file) and inserts one repeater per planned port net:
# port net -> repeater/A, repeater/Y -> new net -> the original sink.  Master OT_CLK_ROOT_CELL (default
# BUFx24_ASAP7_75t_R).  Fail closed: a port that needs a repeater and gets no site stops CTS.
# Runs once per design (guard: an existing instance clk_root_rep_<net>).  'export OT_CLK_ROOT_CROSS = 0' = off.
proc ot_crc_run {} {
  if {[info exists ::env(OT_CLK_ROOT_CROSS)] && $::env(OT_CLK_ROOT_CROSS) eq "0"} { puts "OT_CLK_ROOT_CROSS off"; return }
  set blk [ord::get_db_block]; set db [ord::get_db]; set U [expr {double([$blk getDefUnits])}]
  set dir [expr {[info exists ::env(RESULTS_DIR)] ? $::env(RESULTS_DIR) : "/tmp"}]
  set py [expr {[info exists ::env(OT_CLK_ROOT_PY)] ? $::env(OT_CLK_ROOT_PY) : "/work/clk_root_cross.py"}]
  set cellname [expr {[info exists ::env(OT_CLK_ROOT_CELL)] ? $::env(OT_CLK_ROOT_CELL) : "BUFx24_ASAP7_75t_R"}]
  set halo [expr {[info exists ::env(OT_CLK_ROOT_HALO_UM)] ? $::env(OT_CLK_ROOT_HALO_UM) : 1.0}]
  set dm [$db findMaster $cellname]
  if {$dm eq "NULL"} { error "OT_CLK_ROOT_CROSS: no master $cellname" }
  set macros {}; set busy {}
  foreach i [$blk getInsts] {
    set b [$i getBBox]
    set r [list [expr {[$b xMin]/$U}] [expr {[$b yMin]/$U}] [expr {[$b xMax]/$U}] [expr {[$b yMax]/$U}]]
    if {[[$i getMaster] isBlock]} { lappend macros "\[[join $r ,]\]" } else {
      lappend busy "\[[lindex $r 1],[lindex $r 3],[lindex $r 0],[lindex $r 2]\]" }
  }
  set rows {}
  foreach r [$blk getRows] { set b [$r getBBox]
    lappend rows [format "{\"box\":\[%.4f,%.4f,%.4f,%.4f\],\"site\":%.4f}" [expr {[$b xMin]/$U}] [expr {[$b yMin]/$U}] \
      [expr {[$b xMax]/$U}] [expr {[$b yMax]/$U}] [expr {[[$r getSite] getWidth]/$U}]] }
  set ports {}
  foreach bt [$blk getBTerms] {
    set n [$bt getNet]
    if {$n eq "NULL" || [$n getSigType] ne "CLOCK" || [$bt getIoType] ne "INPUT"} continue
    set bp [lindex [$bt getBPins] 0]; if {$bp eq ""} continue
    set bx [lindex [$bp getBoxes] 0]
    set px [expr {([$bx xMin]+[$bx xMax])/2.0/$U}]; set pyy [expr {([$bx yMin]+[$bx yMax])/2.0/$U}]
    set sk {}
    foreach it [$n getITerms] { set ii [$it getInst]; set ib [$ii getBBox]
      set ok 1; catch { set xy [$it getAvgXY]; set sx [expr {[lindex $xy 1]/$U}]; set sy [expr {[lindex $xy 2]/$U}]; if {![lindex $xy 0]} { set ok 0 } }
      if {![info exists sx] || !$ok} { set sx [expr {([$ib xMin]+[$ib xMax])/2.0/$U}]; set sy [expr {([$ib yMin]+[$ib yMax])/2.0/$U}] }
      lappend sk [format "{\"inst\":\"%s\",\"xy\":\[%.4f,%.4f\],\"macro\":%s}" [$ii getName] $sx $sy [expr {[[$ii getMaster] isBlock] ? "true" : "false"}]]
      unset sx sy }
    lappend ports [format "{\"net\":\"%s\",\"port\":\[%.4f,%.4f\],\"sinks\":\[%s\]}" [$n getName] $px $pyy [join $sk ,]]
  }
  set in "$dir/clk_root_cross.in.json"; set out "$dir/clk_root_cross.out.json"
  set f [open $in w]
  puts $f [format "{\"macros\":\[%s\],\"halo\":%s,\"rows\":\[%s\],\"busy\":\[%s\],\"cell_w\":%.4f,\"ports\":\[%s\]}" \
    [join $macros ,] $halo [join $rows ,] [join $busy ,] [expr {[$dm getWidth]/$U}] [join $ports ,]]
  close $f
  if {[catch {exec python3 -I $py plan $in $out} msg]} { error "OT_CLK_ROOT_CROSS: plan failed: $msg" }
  set f [open $out r]; set txt [read $f]; close $f
  set n 0
  foreach m [regexp -all -inline {\{[^{}]*"net": "[^"]+"[^{}]*"x": [-0-9.e]+[^{}]*\}} $txt] {
    regexp {"net": "([^"]+)"} $m -> net; regexp {"x": ([-0-9.e]+)} $m -> x; regexp {"y": ([-0-9.e]+)} $m -> y
    regexp {"reason": "([^"]+)"} $m -> why
    set nm "clk_root_rep_[regsub -all {[^A-Za-z0-9_]} $net _]"
    if {[$blk findInst $nm] ne "NULL"} { puts "OT_CLK_ROOT_CROSS $net: $nm already present"; continue }
    set pn [$blk findNet $net]; set its [$pn getITerms]
    if {[llength $its] != 1} { error "OT_CLK_ROOT_CROSS: $net has [llength $its] sinks at apply time" }
    set sink [lindex $its 0]
    set inst [odb::dbInst_create $blk $dm $nm]
    set row ""; foreach r [$blk getRows] { set b [$r getBBox]; if {abs([$b yMin] - round($y*$U)) <= 1} { set row $r; break } }
    $inst setOrient [expr {$row ne "" ? [$row getOrient] : "R0"}]
    $inst setLocation [expr {round($x*$U)}] [expr {round($y*$U)}]; $inst setPlacementStatus PLACED
    set nn [odb::dbNet_create $blk "${nm}_n"]; $nn setSigType CLOCK
    odb::dbITerm_disconnect $sink; $sink connect $nn
    set a ""; set yv ""
    foreach t [$inst getITerms] { set mt [$t getMTerm]; if {[$mt getSigType] ne "SIGNAL"} continue
      if {[$mt getIoType] eq "INPUT"} { set a $t } elseif {[$mt getIoType] eq "OUTPUT"} { set yv $t } }
    $a connect $pn; $yv connect $nn
    incr n
    puts [format "OT_CLK_ROOT_CROSS %s (%s): %s at %.3f %.3f" $net $why $nm $x $y]
  }
  if {$n} { global_connect; puts "OT_CLK_ROOT_CROSS inserted $n root repeater(s)" } else { puts "OT_CLK_ROOT_CROSS none needed" }
}
ot_crc_run
