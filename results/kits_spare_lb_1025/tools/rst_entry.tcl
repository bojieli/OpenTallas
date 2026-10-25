# KITS-SPARE/LB 2026-10-25 (GEOM-REVIEW-2 04:38 ve_s/ve_m condition, decision 13 wavefront entry): the reset
# synchroniser (ot_rst_relay sync_q, the entry stage of the core reset) sits FIRM at the rst_n pin through GPL, like
# every data pin register; the per-region relay copies (relay_q) stay at their regions by design.
# Sourced from face_flops.tcl inside its uplevel #0 block, before ff_out is closed.
set re_bt [$ff_blk findBTerm rst_n]
if {$re_bt eq "NULL" || $re_bt eq ""} { error "rst_entry: no rst_n port" }
set re_bb [[lindex [$re_bt getBPins] 0] getBBox]
set re_x [expr {([$re_bb xMin] + [$re_bb xMax]) / 2}]; set re_y [expr {([$re_bb yMin] + [$re_bb yMax]) / 2}]
set re_n 0
foreach i [$ff_blk getInsts] {
  set n [$i getName]
  if {![string match "*u_rst*sync_q*" $n] || ![ff_is_ff $i]} continue
  set got [ff_put_near $i $re_x $re_y]
  if {$got eq ""} { error "rst_entry: no site for $n" }
  puts $ff_out "$n\trst\t[expr {[lindex $got 0] / double($ff_dbu)}]\t[expr {[lindex $got 1] / double($ff_dbu)}]\trst_n"
  incr re_n
}
if {$re_n < 2} { error "rst_entry: expected >= 2 u_rst sync flops, found $re_n" }
puts "OT_RST_ENTRY placed $re_n reset synchroniser flops FIRM at rst_n ([expr {$re_x/double($ff_dbu)}],[expr {$re_y/double($ff_dbu)}])"
