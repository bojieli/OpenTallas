# HBM-CORES-KITS-10 (COORD ASK YES 10-29 05:35): ring_ag qid -> strap_qid (OWNER 10-25 option B ID strap, tied at the parent,
# false_path, no pin register). Netlist ECO: remove the qid face register (DFF + its INV + any hold buffers on the port net),
# drive the former qid__fq loads straight from the port, rename the port/net qid[b] -> strap_qid[b]. Fail-closed checks.
# env: ECO_IN ECO_OUT [ECO_V] ; usable on 1_synth.odb (gate LEC/face_guard view) and on placed/CTS/GRT odbs.
read_db $::env(ECO_IN)
set block [ord::get_db_block]
proc nm {o} { return [string map {"\\" ""} [$o getName]] }
set total_del 0
foreach b {0 1} {
  set bt [$block findBTerm "qid\[$b\]"]
  if {$bt eq "NULL" || $bt eq ""} { error "no BTerm qid\[$b\]" }
  set pn [$bt getNet]
  set qn ""
  foreach n [$block getNets] { if {[nm $n] eq "qid__fq\[$b\]"} { set qn $n; break } }
  if {$qn eq ""} { error "no net qid__fq\[$b\]" }
  # BFS from the port net to qid__fq[b]
  set del {}; set midnets {}; set front [list $pn]; set seen [dict create]
  while {[llength $front]} {
    set nf {}
    foreach n $front {
      foreach it [$n getITerms] {
        if {[$it isInputSignal] == 0} continue
        set inst [$it getInst]; set in [nm $inst]
        if {[dict exists $seen $in]} continue
        dict set seen $in 1
        set m [[$inst getMaster] getName]
        if {![regexp {^(DFF|HB|BUF|INV)} $m]} { error "unexpected cell $in ($m) on qid\[$b\] face path" }
        lappend del $inst
        foreach o [$inst getITerms] {
          if {[$o isOutputSignal]} {
            set on [$o getNet]
            if {$on eq "NULL" || $on eq ""} continue
            if {[nm $on] eq [nm $qn]} continue
            lappend midnets $on; lappend nf $on
          }
        }
      }
    }
    set front $nf
    if {[llength $del] > 16} { error "face path for qid\[$b\] too large: [llength $del]" }
  }
  set ndff 0; foreach i $del { if {[string match DFF* [[$i getMaster] getName]]} {incr ndff} }
  if {$ndff != 1} { error "qid\[$b\]: expected exactly 1 face DFF, found $ndff" }
  # move qid__fq loads to the port net
  set nl 0
  foreach it [$qn getITerms] {
    if {[$it isInputSignal] && [lsearch -exact $del [$it getInst]] < 0} { $it disconnect; $it connect $pn; incr nl }
  }
  puts "OT_STRAP_ECO qid\[$b\] delete [llength $del] insts ([join [lmap i $del {set x "[nm $i]:[[$i getMaster] getName]"}] { }]) moved $nl loads"
  foreach i $del { odb::dbInst_destroy $i; incr total_del }
  foreach n $midnets { if {[llength [$n getITerms]] == 0} { odb::dbNet_destroy $n } }
  if {[llength [$qn getITerms]] == 0} { odb::dbNet_destroy $qn } else { error "qid__fq\[$b\] still has iterms" }
  if {![$bt rename "strap_qid\[$b\]"]} { error "BTerm rename failed" }
  catch {$pn rename "strap_qid\[$b\]"}
  puts "OT_STRAP_ECO port [nm $bt] net [nm $pn] loads [llength [$pn getITerms]]"
}
if {[info exists ::env(ECO_FIRM)]} {
  set nf 0
  foreach i [$block getInsts] { if {[string match {clkbuf_*} [$i getName]] || [string match {mp_isl*} [$i getName]]} { $i setPlacementStatus FIRM; incr nf } }
  puts "OT_FROZEN_CLOCK_CELLS $nf"
}
puts "OT_STRAP_ECO_DONE deleted $total_del"
write_db $::env(ECO_OUT)
exit
