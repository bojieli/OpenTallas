# SERDES-H-FORM reset cohort graph (S81-SERDES-GEN 11-17): CORE / TAP / MACRO / NODE / FANIN rows of the CURRENT placed block,
# the input of reset_cohort_model.py.  Ported from the H17 hand extractor H_final_geometry.tcl (graph part only; the FIRM-identity and
# authority reports stay hand-side).  Read only: no design mutation.  Usage: source this file, then ot_serdes_reset_graph OUT.tsv
namespace eval ot_rg {
proc run {out} {
 global rr_clock_re
 set ::rr_clock_re [expr {[info exists ::env(OT_RESET_GRAPH_CLOCK_RE)] ? $::env(OT_RESET_GRAPH_CLOCK_RE) : {^clk(?:_t[0-9]+)?$}}]
 set b [ord::get_db_block];set dbu [expr {double([$b getDbUnitsPerMicron])}]
 proc ck {i} {
  foreach p [$i getITerms] {
   if {[[$p getMTerm] getName] in {CLK CLKN CK CKN}} {return $p}
  }
  return {}
 }
 proc sources {net depth seen} {
  global rr_clock_re
  if {$net eq "NULL" || $net eq {} || $depth<=0 || [dict exists $seen [$net getName]]} {return {}}
  dict set seen [$net getName] 1;set out {}
  foreach p [$net getITerms] {
   if {[[$p getMTerm] getIoType] ne "OUTPUT"} continue
   set i [$p getInst];set n [$i getName];set clock [ck $i]
   if {[regexp {(?:^|[/.])u_rrl_([0-9]+)[/.]} $n -> id] && $clock ne {} && [$clock getNet] ne "NULL" && [regexp $rr_clock_re [[$clock getNet] getName]]} {dict set out $id 1;continue}
   if {$clock ne {} && [regexp {(?:^|[/.])u_cland_(?:reset_rst_rl|collect_rst_rl)_[0-9]+[/.]} $n]} {dict set out root 1;continue}
   if {$clock ne {} || [[$i getMaster] isBlock]} continue
   foreach inp [$i getITerms] {
    if {[[$inp getMTerm] getIoType] ne "INPUT" || [[$inp getMTerm] getName] in {VDD VSS VPWR VGND}} continue
    set out [dict merge $out [sources [$inp getNet] [expr {$depth-1}] $seen]]
   }
  }
  return $out
 }
 proc fanin_tokens {d} {
  set ids [lsort -integer [lsearch -all -inline -regexp [dict keys $d] {^[0-9]+$}]]
  if {[dict exists $d root]} {lappend ids root}
  return [join $ids ,]
 }
 set f [open $out w]
 set c [$b getCoreArea];puts $f "CORE\t[expr {[$c xMin]/$dbu}]\t[expr {[$c yMin]/$dbu}]\t[expr {[$c xMax]/$dbu}]\t[expr {[$c yMax]/$dbu}]"
 foreach p [$b getBTerms] {
  if {![regexp $::rr_clock_re [$p getName]]} continue
  set z [$p getBBox];puts $f "TAP\t[$p getName]\t[expr {([$z xMin]+[$z xMax])/(2*$dbu)}]\t[expr {([$z yMin]+[$z yMax])/(2*$dbu)}]"
 }
 foreach i [$b getInsts] {
  set n [$i getName];set m [$i getMaster]
  if {[$m isBlock]} {
   set z [$i getBBox];puts $f "MACRO\t$n\t[expr {[$z xMin]/$dbu}]\t[expr {[$z yMin]/$dbu}]\t[expr {[$z xMax]/$dbu}]\t[expr {[$z yMax]/$dbu}]"
  }
  set p [ck $i];if {$p eq {} || [$p getNet] eq "NULL"} continue
  if {![regexp $::rr_clock_re [[$p getNet] getName]]} continue
  set kind {};set id {}
  if {[regexp {(?:^|[/.])u_rrl_([0-9]+)[/.]} $n -> id]} {set kind RRL
  } elseif {[regexp {(?:^|[/.])u_cland_collect_rst_rl_([0-9]+)[/.]} $n -> id]} {set kind COLLECTOR
  } elseif {[regexp {(?:^|[/.])u_enc[/.]} $n]} {set kind ENCODER;set id enc}
  if {$kind eq {}} continue
  lassign [$i getLocation] x y
  puts $f "NODE\t$kind\t$id\t$n\t[expr {$x/$dbu}]\t[expr {$y/$dbu}]\t[$i getPlacementStatus]\t[[$p getNet] getName]"
  if {$kind eq "ENCODER"} continue
  foreach inp [$i getITerms] {
   set pin [[$inp getMTerm] getName]
   if {$pin ni {D RESETN SETN}} continue
   puts $f "FANIN\t$kind\t$id\t$n\t$pin\t[ot_rg::fanin_tokens [sources [$inp getNet] 12 {}]]"
  }
 }
 close $f
}
}
proc ot_serdes_reset_graph {out} {ot_rg::run $out}
