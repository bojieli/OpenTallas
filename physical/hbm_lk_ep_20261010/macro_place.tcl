# [link] 2026-10-10 hfd_lk_ep: the NS retry-pipeline macros (690 x 460) in one row across the block's middle, R0;
# die-side flit pins on the north face, SerDes lane pins on the south face (route.sh --pin-region).
set n 0
foreach inst [lsort [lmap i [[ord::get_db_block] getInsts] {expr {[[$i getMaster] getName] eq "ot_hbm_link_retry_pipeline" ? [$i getName] : [continue]}}]] {
  set x [expr {60.0 + $n * 760.0}]
  set y $::env(OT_LKEP_MY)
  place_macro -macro_name $inst -location [list $x $y] -orientation R0
  incr n
}
puts "OT_LKEP macros placed: $n"
