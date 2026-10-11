# [link] 2026-10-10 hfd_lk_ep in the R25GQ slot (1,503.36 x 993.6; all die pins on the EAST face: phy y 0.6-188,
# f_lk y 783-993): two retry macros in the west column, the third mid-height in the east column, so the SerDes-side
# logic (gearbox, CRC, sub FIFOs) owns the south-east corner beside phy and the coll-side logic (TX queue, merge) the
# north-east corner beside f_lk.
set pos {{19.44 19.44} {19.44 513.0} {749.52 266.76}}
set n 0
foreach inst [lsort [lmap i [[ord::get_db_block] getInsts] {expr {[[$i getMaster] getName] eq "ot_hbm_link_retry_pipeline" ? [$i getName] : [continue]}}]] {
  place_macro -macro_name $inst -location [lindex $pos $n] -orientation R0
  incr n
}
puts "OT_LKEP macros placed: $n"
