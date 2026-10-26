# el1011-ds-coll: child placement of the cb parent (tools/s81_ph/s81_ph_coll_cbh_parent.py)
set ot_at [dict create]
dict set ot_at {u_rw} [list 40.1760 41.0400 R0]
dict set ot_at {u_f} [list 183.6000 41.0400 R0]
dict set ot_at {u_q0} [list 278.6400 41.0400 R0]
dict set ot_at {g_q[1].u_q} [list 386.6400 41.0400 R0]
dict set ot_at {g_q[2].u_q} [list 494.6400 41.0400 R0]
dict set ot_at {g_q[3].u_q} [list 602.6400 41.0400 R0]
dict set ot_at {g_q[4].u_q} [list 710.6400 41.0400 R0]
dict set ot_at {u_re} [list 818.6400 41.0400 MY]
set ot_n 0
foreach ot_i [[ord::get_db_block] getInsts] {
  set ot_nm [$ot_i getName]; set ot_k [string map {"\\" ""} $ot_nm]
  if {![dict exists $ot_at $ot_k]} continue
  lassign [dict get $ot_at $ot_k] ot_x ot_y ot_o
  place_macro -macro_name $ot_nm -location [list $ot_x $ot_y] -orientation $ot_o; incr ot_n
}
if {$ot_n != 8} { error "place_macros_cbh: placed $ot_n children (expected 8)" }
puts "place_macros_cbh: $ot_n children placed"
