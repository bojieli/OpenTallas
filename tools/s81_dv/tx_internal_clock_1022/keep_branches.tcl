# Preserve only the two source RTL region buffers, before floorplan and GPL
# remove_buffers. Output nets remain mutable for the source-owned spine builder.
set tx_branch_cells {}
foreach n {u_ot_pr_core.u_sm.g_s.g_ring.u_ck_a/u_ck u_ot_pr_core.u_sm.g_s.g_ring.u_ck_b/u_ck} {
 set c [get_cells -quiet $n]
 if {[llength $c]!=1 || [get_full_name $c] ne $n || [get_property $c ref_name] ne "BUFx24_ASAP7_75t_R"} {
  set tx_candidates {}
  foreach i [[ord::get_db_block] getInsts] {
   if {[string match *g_ring*u_ck* [$i getName]]} {
    lappend tx_candidates [list [$i getName] [[$i getMaster] getName]]
    if {[llength $tx_candidates]>=8}break
   }
  }
  error "TX_BRANCH_KEEP missing exact source clock buffer $n; actual bounded branch candidates: $tx_candidates"
 }
 set lc [get_lib_cells -quiet -of_objects $c]
 set ip [get_pins -quiet -of_objects $c -filter "direction == input"]
 set op [get_pins -quiet -of_objects $c -filter "direction == output"]
 if {[llength $lc]!=1 || ![get_property $lc is_buffer] || [llength $ip]!=1 || [llength $op]!=1
  || [get_property $ip lib_pin_name] ne "A" || [get_property $op lib_pin_name] ne "Y"} {
  error "TX_BRANCH_KEEP wrong actual Liberty function/pins $n"
 }
 lappend tx_branch_cells $c
}
set_dont_touch $tx_branch_cells
puts "TX_BRANCH_KEEP protected exactly two unary source clock buffer cells; output nets mutable"
