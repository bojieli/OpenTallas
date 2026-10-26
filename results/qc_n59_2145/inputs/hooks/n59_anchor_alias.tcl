# The unkept dr_o[516] publication shares its value with a kept em_c register.
# Resolve this single documented name change from the actual boundary D cone;
# no missing anchors are skipped, and a multi-register cone is rejected.
proc n59r_find_norm {wanted} {
 global n59r_blk n59r_norm
 if {![info exists n59r_norm]} {
  set n59r_norm {}
  foreach i [$n59r_blk getInsts] {
   set raw [string map [list "\\" ""] [$i getName]]
   if {[dict exists $n59r_norm $raw]} {error "N59_REACH405 ambiguous canonical instance $raw"}
   dict set n59r_norm $raw $i
  }
 }
 if {![dict exists $n59r_norm $wanted]} {error "N59_REACH405 missing canonical instance $wanted"}
 return [dict get $n59r_norm $wanted]
}
proc n59r_source_regs {net depth} {
 global n59r_seen
 if {$net eq "NULL"} {return {}}
 if {$depth>16} {error "N59_REACH405 alias cone exceeds16combinational levels"}
 set id [$net getId]
 if {[dict exists $n59r_seen $id]} {return {}}
 dict set n59r_seen $id 1
 set out {}
 foreach it [$net getITerms] {
  if {![$it isOutputSignal]} continue
  set i [$it getInst];set m [$i getMaster]
  if {[regexp {DFF|SDF} [$m getName]]} {lappend out [$i getName];continue}
  if {[$m isBlock]} {error "N59_REACH405 alias reaches a macro"}
  foreach ii [$i getITerms] {
   if {[$ii isInputSignal] && ![$ii isClocked]} {lappend out {*}[n59r_source_regs [$ii getNet] [expr {$depth+1}]]}
  }
 }
 return [lsort -unique $out]
}
proc n59r_resolve_alias {name} {
 global n59r_blk n59r_seen
 set raw [string map [list "\\" ""] $name]
 if {[regexp {^(u_bound[.]u_pd([13])_[^.]+)[.]r\[([0-9]+)\]\$_DFF_P_$} $raw -> prefix depth stage]} {
  if {$stage != $depth-1} {error "N59_REACH405 missing non-final delay stage $name"}
  # Validate the exact W1/D instance and direct last-state publication in
  # the selected source; q and r[D-1] are the same physical state value.
  set f [open /work/rtl/qfd_qc_native59_part_bound.sv];set text [read $f];close $f
  set instname [lindex [split $prefix .] end]
  set re [format {ot_dp_dly\s*#\(\.W\(1\),\s*\.D\(%d\)\)\s+%s\s+\(} $depth $instname]
  if {![regexp $re $text]} {error "N59_REACH405 delay alias source shape mismatch $name"}
  set f [open /work/rtl/bind_cells_kit.sv];set text [read $f];close $f
  if {[string first {assign q = r[D-1];} $text]<0} {error "N59_REACH405 direct delay-state alias missing"}
  set qname [format {%s.q$_DFF_P_} $prefix]
  set i [n59r_find_norm $qname]
  if {![regexp {DFF} [[$i getMaster] getName]]} {error "N59_REACH405 delay alias is not one physical FF"}
  global n59r_alias_count;incr n59r_alias_count
  if {$n59r_alias_count<=4} {puts "N59_REACH405 exact final-delay-state alias: $name -> [$i getName]"}
  return $i
 }
 if {$raw ne {u_bound.u_core.u_svc.dr_o[516]$_DFF_PN0_}} {error "N59_REACH405 missing physical anchor $name"}
 set landing [n59r_find_norm {u_bound.u_bout_dr_o/q[516]$_DFF_P_}]
 set d [$landing findITerm D]
 if {$d eq "NULL"} {error "N59_REACH405 alias landing has no D"}
 set n59r_seen {};set regs [n59r_source_regs [$d getNet] 0]
 if {[llength $regs]!=1} {error "N59_REACH405 alias boundary-D cone is not one register: $regs"}
 set actual [lindex $regs 0]
 set actual_raw [string map [list "\\" ""] $actual]
 if {$actual_raw ne {u_bound.u_core.u_svc.g_emb_relay.em_c[0][4]$_DFF_PN0_}} {error "N59_REACH405 unexpected dr_o516 physical representative $actual"}
 puts "N59_REACH405 exact boundary-D alias: $name -> $actual"
 return [$n59r_blk findInst $actual]
}
