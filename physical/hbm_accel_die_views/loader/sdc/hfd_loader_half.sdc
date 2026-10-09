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
# CFGREP (drive-2125 2026-10-08, REVIEW_20261008 DQ1; 0 cycles): registered copies of the cfg-chain valids, one per skid
# storage group (RG 8), kept ot_hfd_oreg1 flops on the core clock.  Source of each copy (a copy registered from cfg[k-1]
# equals cfg[k] every cycle; cfg is the die view's quasi-static stand-in for memory-side inputs with no die net):
#   u_cfgrep_rsp[0..7].u   = cfg[140]  (rsp_v[0] -> u_ld.u_sk_rsp[0].g_rep.u, storage group 0..7)
#   u_cfgrep_rsp[8..15].u  = cfg[141]  (rsp_v[1] -> u_ld.u_sk_rsp[1].g_rep.u, storage group 0..7)
#   u_cfgrep_mr[0..7].u    = cfg[65]   (m_rvalid -> u_ld.u_sk_m_r[0].g_rep.u, storage group 0..7)
# Copy -> slice paths stay single-cycle face <-> slice paths (no exception); the copies only split the enable fanout.
set ot_cfgrep [get_cells -quiet {u_cfgrep_rsp* u_cfgrep_mr*}]
puts "OT_LOADER_CFGREP copies matched: [llength $ot_cfgrep] (sources cfg\[140\] x8, cfg\[141\] x8, cfg\[65\] x8)"
