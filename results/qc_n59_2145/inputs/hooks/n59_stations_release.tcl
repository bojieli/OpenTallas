# PATH-QC-N59-PROTO: return the QB_STN station flops (n59_stations.tcl, FIRM) to PLACED before detailed placement.
set n59rel_blk [ord::get_db_block]; set n59rel_n 0
foreach i [$n59rel_blk getInsts] {
  if {[regexp {g_wif\.g_w\\?\[[0-9]+\\?\]\.g_stn[./]u_s[12][./]|g_rstn\.g_w\\?\[[0-9]+\\?\]\.?[./]?u_sr[./]} [$i getName]] && [$i getPlacementStatus] eq "FIRM"} {
    $i setPlacementStatus PLACED; incr n59rel_n }
}
puts "OT_N59_STN released $n59rel_n station flops"
