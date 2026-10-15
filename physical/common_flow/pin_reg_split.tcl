# PRE_GLOBAL_PLACE hook (el1014-root-recipe2, 2026-10-14; ref_tile kit recipe 2, sourced FIRST by the kit pre_gpl.tcl):
# ONE DEDICATED LAUNCH FLOP PER OUTPUT PIN.
#
# Measured (Qwen edge, 10-14 07:10): synthesis folds identical pin registers into one flop (opt_merge after flatten:
# cache R2 f_addr bits equal across lane groups -> one flop -> INV fanout 7 -> 7 output pins).  Such a flop can sit at one
# pin only; io_flop_at_pins.tcl cannot anchor it (its walk needs a single-load chain) so timing-driven GPL leaves it in
# the core, and every pin it drives pays the wire: R2 123 outputs over the 220 ps native launch budget (worst 239.6 ps),
# slab col m5 331 ps.  An RTL-shared register (assign a = r; assign b = r;) and a pin register that also feeds internal
# logic have the same defect.  physical/common_flow/ot_keep_regs.tcl (OT_KEEP_PIN_REGS=1) stops the merge of distinct
# top-level pin registers in synthesis; this hook is the netlist guarantee for everything else.
#
# For every OUTPUT port whose net is driven by a DFF directly or through <= OT_PRS_HOPS single-input INV / BUF / HB
# cells: when any net of that chain also reaches another load (a second port, an internal cell, a second BTerm), the
# chain (flop + its buffers) is CLONED for this port: the clone flop takes the same D / clock / reset nets (register
# duplication, function unchanged, 0 cycles), its buffers are fresh copies, and the port moves to a new net driven only
# by the cloned chain.  Cells left without any load afterwards (the old chain of a flop that now drives nothing) are
# deleted.  The result: every flop-driven output has a launch flop whose Q net feeds that port's chain and nothing
# else, so io_flop_at_pins.tcl anchors it at its own pin.
#   OT_PRS_HOPS (default 4)   cells walked from the port back to the flop, the flop included
#   OT_PRS_PORT_RE            only ports whose name matches (default: every output port)
#   OT_PRS_MAX (default 4096) refuse (error) above this many clones: a tile that needs more is an RTL problem
# No procs: ORFS sources step hooks inside a proc.
set ot_ps_blk [ord::get_db_block]
set ot_ps_hops [expr {[info exists ::env(OT_PRS_HOPS)] && $::env(OT_PRS_HOPS) ne "" ? $::env(OT_PRS_HOPS) : 4}]
set ot_ps_re [expr {[info exists ::env(OT_PRS_PORT_RE)] ? $::env(OT_PRS_PORT_RE) : ""}]
set ot_ps_max [expr {[info exists ::env(OT_PRS_MAX)] && $::env(OT_PRS_MAX) ne "" ? $::env(OT_PRS_MAX) : 4096}]
set ot_ps_n 0; set ot_ps_ok 0; set ot_ps_skip 0; set ot_ps_cells 0; set ot_ps_del 0
set ot_ps_flops [dict create]
# deterministic order (by port name), so a re-run of the same netlist names the clones the same
set ot_ps_bts {}
foreach bt [$ot_ps_blk getBTerms] {
  if {[$bt getIoType] ne "OUTPUT"} continue
  if {$ot_ps_re ne "" && ![regexp -- $ot_ps_re [$bt getName]]} continue
  lappend ot_ps_bts [list [$bt getName] $bt]
}
foreach pr [lsort -index 0 $ot_ps_bts] {
  set bt [lindex $pr 1]
  set net [$bt getNet]
  if {$net eq "NULL" || $net eq ""} continue
  if {[$net getSigType] ne "SIGNAL"} continue
  # walk port -> flop; chain = {cell ...} from the port side, nets = the output net of each chain cell (port side first)
  set chain {}; set nets {}; set ff ""; set cn $net
  for {set hop 0} {$hop < $ot_ps_hops} {incr hop} {
    set dv ""
    foreach it [$cn getITerms] { if {[$it isOutputSignal]} { set dv $it; break } }
    if {$dv eq ""} break
    set di [$dv getInst]; set dm [[$di getMaster] getName]
    if {[string match "DFF*" $dm] || [string match "ASYNC_DFF*" $dm]} { set ff $di; lappend nets $cn; break }
    if {![regexp {^(BUF|INV|HB)} $dm]} break
    set ain [$di findITerm A]
    if {$ain eq "NULL" || $ain eq ""} break
    lappend chain $di; lappend nets $cn
    set cn [$ain getNet]
    if {$cn eq "NULL" || $cn eq ""} break
  }
  if {$ff eq ""} { incr ot_ps_skip; continue }
  # exclusive: every net of the chain has exactly one consumer (the next chain cell, or this one BTerm at the port)
  set excl 1
  for {set k 0} {$k < [llength $nets]} {incr k} {
    set n [lindex $nets $k]
    set loads 0
    foreach it [$n getITerms] { if {[$it isInputSignal]} { incr loads } }
    set nb [llength [$n getBTerms]]
    if {$k == 0} {
      if {$loads != 0 || $nb != 1} { set excl 0; break }
    } elseif {$loads != 1 || $nb != 0} { set excl 0; break }
  }
  if {$excl && ![dict exists $ot_ps_flops [$ff getName]]} {
    dict set ot_ps_flops [$ff getName] 1
    incr ot_ps_ok
    continue
  }
  if {$ot_ps_n >= $ot_ps_max} { error "OT_PRS: more than $ot_ps_max shared pin flops (OT_PRS_MAX): fix the RTL" }
  # clone flop: every non-output signal / clock pin on the same net (D, CLK, RESET, SET ...), the chain output only
  set q ""; set fq [lindex $nets end]
  foreach it [$ff getITerms] { if {[$it isOutputSignal] && [$it getNet] eq $fq} { set q [[$it getMTerm] getName] } }
  set cf [odb::dbInst_create $ot_ps_blk [$ff getMaster] [format "ot_prs_%05d_ff" $ot_ps_n]]
  foreach it [$ff getITerms] {
    set mt [$it getMTerm]
    if {[$it isOutputSignal]} continue
    set st [$mt getSigType]
    if {$st eq "POWER" || $st eq "GROUND"} continue
    set n2 [$it getNet]; if {$n2 eq "NULL" || $n2 eq ""} continue
    [$cf findITerm [$mt getName]] connect $n2
  }
  set cur [odb::dbNet_create $ot_ps_blk [format "ot_prs_%05d_q" $ot_ps_n]]
  [$cf findITerm $q] connect $cur
  incr ot_ps_cells
  # buffers, flop side first
  set k 0
  foreach ci [lreverse $chain] {
    set cc [odb::dbInst_create $ot_ps_blk [$ci getMaster] [format "ot_prs_%05d_b%d" $ot_ps_n $k]]
    [$cc findITerm A] connect $cur
    set cur [odb::dbNet_create $ot_ps_blk [format "ot_prs_%05d_n%d" $ot_ps_n $k]]
    [$cc findITerm Y] connect $cur
    incr ot_ps_cells; incr k
  }
  $bt disconnect
  $bt connect $cur
  # the old chain may now drive nothing: delete load-less cells from the port side back to (and including) the flop
  set gone 1
  foreach ci [concat $chain [list $ff]] {
    if {!$gone} break
    set used 0
    foreach it [$ci getITerms] {
      if {![$it isOutputSignal]} continue
      set on [$it getNet]; if {$on eq "NULL" || $on eq ""} continue
      if {[llength [$on getBTerms]] > 0} { set used 1 }
      foreach l [$on getITerms] { if {[$l isInputSignal]} { set used 1 } }
    }
    if {$used} { set gone 0; break }
    set dead {}
    foreach it [$ci getITerms] {
      set on [$it getNet]
      if {[$it isOutputSignal] && $on ne "NULL" && $on ne ""} { lappend dead $on }
    }
    odb::dbInst_destroy $ci
    foreach on $dead { if {[llength [$on getITerms]] == 0 && [llength [$on getBTerms]] == 0} { odb::dbNet_destroy $on } }
    incr ot_ps_del
  }
  dict set ot_ps_flops [$cf getName] 1
  incr ot_ps_n
}
puts "OT_PRS: $ot_ps_ok output pins already on a dedicated flop, $ot_ps_n pins split onto a cloned flop ($ot_ps_cells cells added, $ot_ps_del load-less cells removed), $ot_ps_skip outputs not flop-driven"
