# Packet SRAM II=1 refill: three 256x256 macros stacked in the centre column, R0.  Read pins (rd_out) are on
# each macro's LEFT edge, write pins (wd_in) on its RIGHT edge (LEF): the read/decode logic and dout pins sit
# in the left channel, the encode logic and din pins in the right channel.  x on the 0.216 um grid, y on 4.32 um
# (row 0.27 x M4 0.048).
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
ot_place {u_q.g_ram[0].storage} 78.624 30.24 R0
ot_place {u_q.g_ram[1].storage} 78.624 86.4 R0
ot_place {u_q.g_ram[2].storage} 78.624 142.56 R0
