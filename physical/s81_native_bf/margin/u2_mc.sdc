# BF unroll-by-2 (ot_s81_bf_native RECUT=3, 2026-10-07): each BF lane chunk chain (ot_v41_chain2u2) runs its two adders,
# accumulator file and pair registers (names hs_*) on hclk = the lane clock gated every other cycle by a local ph flop,
# so they launch and capture only on gated edges: paths among them get two clock periods (multicycle setup 2 / hold 1).
# The full-rate input pair registers and output registers stay single cycle.  The verdict check greps OT_BF_U2.
if {[catch {
  set ot_h {}
  foreach ot_c [all_registers] {
    if {[string match {*.hs_*} [get_full_name $ot_c]]} { lappend ot_h $ot_c }
  }
  if {[llength $ot_h] > 0} {
    set_multicycle_path -setup 2 -from $ot_h -to $ot_h
    set_multicycle_path -hold 1 -from $ot_h -to $ot_h
    puts "OT_BF_U2 multicycle on [llength $ot_h] registers"
  } else {
    puts "OT_BF_U2 WARNING no hs_* registers matched (expected only before synthesis)"
  }
} ot_err]} { puts "OT_BF_U2 WARNING not applied: $ot_err" }
