# KV-SENDER-SKEW 11-24 (COORD ruling, plan clock.fwd_export.<type> = {"from": "leaf", "match_insertion": true};
# landing_contract.export_leaf_rows writes /work/fwd_export_leaf.txt, gen_phys hooks this file into the kit cts_post.tcl
# before the first balance pass and again after leaf_affinity.tcl).
# The fwd_buffer export (landing_exports.tcl) sits on the ROOT net of its source tap: TritonCTS keeps a non-register load
# there, so fclk leaves the port at root insertion (~115 ps) while the ring's last-station flops launch at leaf insertion
# (~400 ps): kv3_pv_v12 A5t5 CTS d = data - fclk max 186..370 ps (target 147).  Here, after CTS, each listed export
# buffer moves its input onto the clock net that drives the CLK pins of the ring's launch flops (the net with the most
# of them, among the flops whose clock comes from the export's source tap port, so the SDC generated clock keeps its
# -source), and the buffer moves next to those flops.  fclk then shares the launch flops' whole tree: same insertion by
# construction, d = clk->q + data wire - export buffer and port wire.  No launch flop on the source tap = error (fail
# closed: the plan must re-site the ring onto the export tap).  Row: `port src buffer npad base...` (base = data port
# names).  npad > 0 (clock.fwd_export.<T>.pad_ps): a chain of npad BUFx4 cells between the leaf and the export buffer
# delays fclk into the data eye (A5t5 what-if: leaf alone leaves d_max 253 ps TT from the output stage, d_min -26;
# the receiver contract is d >= -385 and d <= ~147, so a uniform delay centres every ring).
proc fel_clk {inst} {
  foreach it [$inst getITerms] { if {[[$it getMTerm] getName] in {CLK CK}} { return $it } }
  return ""
}
# launch register of an output port: up through single-input cells (output buffers, inverters) to a cell with CLK
proc fel_launch {bt} {
  set net [$bt getNet]
  for {set hop 0} {$hop < 64} {incr hop} {
    if {$net eq "NULL"} { return "" }
    set drv {}; foreach it [$net getITerms] { if {[$it isOutputSignal]} { lappend drv $it } }
    if {[llength $drv] != 1} { return "" }
    set inst [[lindex $drv 0] getInst]
    if {[fel_clk $inst] ne ""} { return $inst }
    set ins {}; foreach it [$inst getITerms] { if {[$it isInputSignal]} { lappend ins $it } }
    if {[llength $ins] != 1} { return "" }
    set net [[lindex $ins 0] getNet]
  }
  return ""
}
# input port at the top of a clock net (through the single-input tree cells), "" if none
proc fel_upport {net} {
  for {set hop 0} {$hop < 1000} {incr hop} {
    if {$net eq "NULL"} { return "" }
    foreach b [$net getBTerms] { if {[$b getIoType] eq "INPUT"} { return [$b getName] } }
    set drv {}; foreach it [$net getITerms] { if {[$it isOutputSignal]} { lappend drv $it } }
    if {[llength $drv] != 1} { return "" }
    set ins {}; foreach it [[[lindex $drv 0] getInst] getITerms] { if {[$it isInputSignal]} { lappend ins $it } }
    if {[llength $ins] != 1} { return "" }
    set net [[lindex $ins 0] getNet]
  }
  return ""
}
proc fwd_export_leaf {tag} {
  set f /work/fwd_export_leaf.txt
  if {![file exists $f]} { puts "OT_FWD_LEAF $tag: no $f"; return }
  set blk [ord::get_db_block]
  set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
  set ca [$blk getCoreArea]
  set lim [expr {20.0 * $dbu}]
  # data ports by base name (scalar `b` or bits `b[i]`)
  set byb [dict create]
  foreach b [$blk getBTerms] {
    if {[$b getIoType] ne "OUTPUT"} continue
    set n [$b getName]; regsub {\[[0-9]+\]$} $n "" k
    dict lappend byb $k $b
  }
  set up [dict create]
  set n 0; set same 0; set moved 0; set bad {}
  set h [open $f]
  while {[gets $h l] >= 0} {
    if {[string match "#*" $l] || [llength $l] < 5} continue
    set port [lindex $l 0]; set src [lindex $l 1]; set bn [lindex $l 2]; set npad [lindex $l 3]
    set bi [$blk findInst $bn]
    if {$bi eq "NULL"} { lappend bad "$port: export buffer $bn missing"; continue }
    set a [$bi findITerm A]
    # pad_ps: npad BUFx4 cells leaf -> ${bn}_pad0 .. -> export buffer (built once; later passes re-hang pad0)
    set chain {}
    if {$npad > 0} {
      if {[$blk findInst ${bn}_pad0] eq "NULL"} {
        set pm [[ord::get_db] findMaster BUFx4_ASAP7_75t_R]
        if {$pm eq "NULL"} { error "OT_FWD_LEAF pad master BUFx4_ASAP7_75t_R missing" }
        lassign [$bi getLocation] bx by
        if {[$a getNet] ne "NULL"} { $a disconnect }
        set prev ""
        for {set k 0} {$k < $npad} {incr k} {
          set pi [odb::dbInst_create $blk $pm ${bn}_pad$k]
          $pi setLocation $bx $by; $pi setPlacementStatus PLACED
          if {$prev ne ""} { [$pi findITerm A] connect $prev }
          set prev [odb::dbNet_create $blk ${bn}_padnet$k]
          $prev setSigType CLOCK
          [$pi findITerm Y] connect $prev
        }
        $a connect $prev
      }
      for {set k 0} {$k < $npad} {incr k} {
        set pi [$blk findInst ${bn}_pad$k]
        if {$pi eq "NULL"} { error "OT_FWD_LEAF $bn pad chain broken at $k" }
        lappend chain $pi
      }
      set a [[lindex $chain 0] findITerm A]
    }
    set nets [dict create]; set tot 0; set xtap 0
    foreach base [lrange $l 4 end] {
      if {![dict exists $byb $base]} continue
      foreach bt [dict get $byb $base] {
        set li [fel_launch $bt]
        if {$li eq ""} continue
        set cn [[fel_clk $li] getNet]
        if {$cn eq "NULL"} continue
        incr tot
        if {![dict exists $up $cn]} { dict set up $cn [fel_upport $cn] }
        if {[dict get $up $cn] ne $src} { incr xtap; continue }
        dict lappend nets $cn $li
      }
    }
    if {![dict size $nets]} { lappend bad "$port: none of $tot launch flop(s) on source tap $src ($xtap on other taps)"; continue }
    set best ""; set bc -1
    foreach cn [lsort [dict keys $nets]] {
      set c [llength [dict get $nets $cn]]
      if {$c > $bc} { set best $cn; set bc $c }
    }
    set fl [dict get $nets $best]
    if {[$a getNet] eq $best} {
      incr same
    } else {
      if {[$a getNet] ne "NULL"} { $a disconnect }
      $a connect $best
      $best setSigType CLOCK
      incr n
    }
    set sx 0; set sy 0
    foreach i $fl { lassign [$i getLocation] x y; set sx [expr {$sx + $x}]; set sy [expr {$sy + $y}] }
    set m [$bi getMaster]
    set cx [expr {min(max(round(double($sx) / [llength $fl]), [$ca xMin]), [$ca xMax] - [$m getWidth])}]
    set cy [expr {min(max(round(double($sy) / [llength $fl]), [$ca yMin]), [$ca yMax] - [$m getHeight])}]
    lassign [$bi getLocation] bx by
    set d [expr {abs($bx - $cx) + abs($by - $cy)}]
    if {$d > $lim && [$bi getPlacementStatus] ni {FIRM LOCKED COVER}} {
      $bi setLocation $cx $cy; $bi setPlacementStatus PLACED
      foreach pi $chain { $pi setLocation $cx $cy; $pi setPlacementStatus PLACED }
      incr moved
    }
    puts [format "OT_FWD_LEAF %s %s <- %s (src %s): %d of %d launch flop(s) on it, %d on other leaves of the tap, %d off the tap, buffer %.1f um from them, %d pad cell(s)" \
      $tag $port [$best getName] $src $bc $tot [expr {$tot - $xtap - $bc}] $xtap [expr {double($d) / $dbu}] $npad]
  }
  close $h
  puts "OT_FWD_LEAF $tag: $n export(s) hung on their launch leaf, $same already there, $moved moved next to their flops, [llength $bad] failed"
  if {[llength $bad]} {
    set fh [open /work/FAIL_POSTCTS a]
    foreach b $bad { puts $fh "FAIL_POSTCTS forwarded clock leaf export $b" }
    close $fh
    error "OT_FWD_LEAF FAIL [llength $bad]: [lindex $bad 0]"
  }
  if {$moved} { detailed_placement }
}
