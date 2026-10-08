# hfd_loader half rate (views agent 2026-10-07, rtl/ot_hfd_loader_half.sv SHARED 1): the core runs on ck gated every
# other cycle (latch + AND clock gate), so every core flop launches and captures only on gated edges: core -> core paths
# get two ck periods (multicycle setup 2 / hold 1).  Core <-> face paths stay single cycle (the handshakes are gated to
# the cycle that ends on a gated edge).  The verdict check greps OT_LOADER_HALF in the sign-off logs.
# SKID (hbm-blocks 2026-10-07, make_loader_half.py --skid): the channel register slices u_ld.u_sk_* are gated-clock
# flops too, so core <-> slice paths join the multicycle set; face <-> slice paths stay single cycle (no core logic).
set ot_core [get_cells -quiet {u_ld.u_core.* u_ld.u_sk_*}]
if {[llength $ot_core] > 0} {
  set_multicycle_path -setup 2 -from $ot_core -to $ot_core
  set_multicycle_path -hold 1 -from $ot_core -to $ot_core
  puts "OT_LOADER_HALF multicycle on [llength $ot_core] core cells"
} else {
  puts "OT_LOADER_HALF WARNING no core cells matched u_ld.u_core.* (expected only before synthesis)"
}
