# Written by tools/qwen_o4_floorplan.py: die-row assembly: 14 plain-tile abstracts, 21.6 um pin-access gaps, glue strips above and below
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

ot_place {g_tile[0].u_tile} 21.6 41.04 R0
ot_place {g_tile[1].u_tile} 1019.52 41.04 R0
ot_place {g_tile[2].u_tile} 2017.44 41.04 R0
ot_place {g_tile[3].u_tile} 3015.36 41.04 R0
ot_place {g_tile[4].u_tile} 4013.28 41.04 R0
ot_place {g_tile[5].u_tile} 5011.2 41.04 R0
ot_place {g_tile[6].u_tile} 6009.12 41.04 R0
ot_place {g_tile[7].u_tile} 7007.04 41.04 R0
ot_place {g_tile[8].u_tile} 8004.96 41.04 R0
ot_place {g_tile[9].u_tile} 9002.88 41.04 R0
ot_place {g_tile[10].u_tile} 10000.8 41.04 R0
ot_place {g_tile[11].u_tile} 10998.72 41.04 R0
ot_place {g_tile[12].u_tile} 11996.64 41.04 R0
ot_place {g_tile[13].u_tile} 12994.56 41.04 R0
puts "ot_place: 14 macros placed"
