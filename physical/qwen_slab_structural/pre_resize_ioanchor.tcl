# PRE_RESIZE_TCL (slab margin m3, 2026-10-06): anchor the boundary registers at their pins.  m2 left them where global
# placement put them (res_q up to 254 ps of wire from its res_in pin, OREG flops ~700 ps from the o_* pins, res_q clock
# insertion spread 818..1030 ps SS), so the "register at the pin" boundary did not hold.  Every flop that captures an
# anchored input port, and every flop (plus its output inverter/buffer) that drives an anchored output port, is moved
# beside its pin; detailed placement legalises.  The register -> register stages behind them (res_q -> a_q -> C7,
# od1 -> od2 -> OREG) absorb the moved wire.  Ports: QSS_ANCHOR_RE (default res_in / o_* / ov).
set qa_re [expr {[info exists ::env(QSS_ANCHOR_RE)] ? $::env(QSS_ANCHOR_RE) : {^(res_in|o_|ov$)}}]
set qa_block [ord::get_db_block]
set qa_core [$qa_block getCoreArea]
set qa_dbu [[$qa_block getTech] getDbUnitsPerMicron]
proc qa_is_seq {inst} { return [regexp {DFF|DHL|DLL|SDF} [[$inst getMaster] getName]] }
proc qa_is_buf {inst} { return [regexp {^(BUF|INV|HB)} [[$inst getMaster] getName]] }
proc qa_put {inst x y} {
  global qa_core
  set w [[$inst getMaster] getWidth]
  set xl [expr {max([$qa_core xMin], min($x, [$qa_core xMax] - $w))}]
  set yl [expr {max([$qa_core yMin], min($y, [$qa_core yMax] - [[$inst getMaster] getHeight]))}]
  $inst setLocation $xl $yl
  $inst setPlacementStatus PLACED
  return $w
}
proc qa_walk {net fwd depth} {
  if {$depth < 0 || $net eq "NULL"} { return {} }
  set next {}
  foreach it [$net getITerms] {
    if {$fwd ? ![$it isInputSignal] : ![$it isOutputSignal]} continue
    lappend next [$it getInst]
  }
  if {[llength $next] != 1} { return {} }
  set i [lindex $next 0]
  if {[qa_is_seq $i]} { return [list $i] }
  if {![qa_is_buf $i]} { return {} }
  foreach jt [$i getITerms] {
    if {[[$jt getMTerm] getSigType] ne "SIGNAL"} continue
    if {$fwd ? ![$jt isOutputSignal] : ![$jt isInputSignal]} continue
    set rest [qa_walk [$jt getNet] $fwd [expr {$depth - 1}]]
    if {[llength $rest]} { return [concat [list $i] $rest] }
  }
  return {}
}
set qa_n 0; set qa_skip 0
foreach bt [$qa_block getBTerms] {
  set name [$bt getName]
  if {![regexp -- $qa_re $name]} continue
  set net [$bt getNet]; if {$net eq "NULL"} { incr qa_skip; continue }
  set bb [$bt getBBox]
  set px [expr {([$bb xMin] + [$bb xMax]) / 2}]; set py [expr {([$bb yMin] + [$bb yMax]) / 2}]
  set right [expr {$px > ([$qa_core xMin] + [$qa_core xMax]) / 2}]
  # walk through port / placement buffers and inverters (<= 4 levels) to the boundary flop; chain is pin-side first
  set chain [qa_walk $net [expr {[$bt getIoType] eq "INPUT"}] 4]
  if {[llength $chain] == 0 || ![qa_is_seq [lindex $chain end]]} { incr qa_skip; continue }
  # pin-side first: [port buffer, flop] (buffer nearest the pin)
  set x [expr {$right ? [$qa_core xMax] : [$qa_core xMin]}]
  foreach i $chain {
    set w [[$i getMaster] getWidth]
    if {$right} { set x [expr {$x - $w}]; qa_put $i $x $py } else { qa_put $i $x $py; set x [expr {$x + $w}] }
    incr qa_n
  }
}
puts "QSS IO anchor: $qa_n instances moved beside their pins ($qa_skip ports skipped), ports $qa_re"
