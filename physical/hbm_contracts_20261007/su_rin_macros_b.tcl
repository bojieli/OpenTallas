# SU result ingress lane: the 64x512 macro has rd_out and the used wd_in bits on its LEFT edge (LEF), so the macro
# sits at the right of the die and all lane logic in the left channel.  x on 0.216 um, y on 4.32 um.
set ot_block [ord::get_db_block]
set ot_lut [dict create]
foreach ot_inst [$ot_block getInsts] {
  if {[[$ot_inst getMaster] isBlock]} {
    dict set ot_lut [string map {"\\" ""} [$ot_inst getName]] [$ot_inst getName]
  }
}
proc ot_place {name x y orient} {
  global ot_lut
  if {![dict exists $ot_lut $name]} { error "ot_place: no macro instance $name" }
  place_macro -macro_name [dict get $ot_lut $name] -location [list $x $y] -orientation $orient
}
ot_place {u_in.u_store} 123.12 21.6 R0
