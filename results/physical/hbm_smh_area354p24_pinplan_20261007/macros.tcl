set ot_n 0
array set ot_xy {
  {t:0:0} {8.64 613.44}
  {t:0:1} {8.64 95.04}
  {b:0} {25.92 8.64}
  {t:1:0} {371.52 613.44}
  {t:1:1} {371.52 95.04}
  {b:1} {388.8 8.64}
  {t:2:0} {734.4 613.44}
  {t:2:1} {734.4 95.04}
  {b:2} {751.68 8.64}
  {t:3:0} {1097.28 613.44}
  {t:3:1} {1097.28 95.04}
  {b:3} {1114.56 8.64}
  {t:4:0} {1900.8 613.44}
  {t:4:1} {1900.8 95.04}
  {b:4} {1918.08 8.64}
  {t:5:0} {2263.68 613.44}
  {t:5:1} {2263.68 95.04}
  {b:5} {2280.96 8.64}
  {t:6:0} {2626.56 613.44}
  {t:6:1} {2626.56 95.04}
  {b:6} {2643.84 8.64}
  {t:7:0} {2989.44 613.44}
  {t:7:1} {2989.44 95.04}
  {b:7} {3006.72 8.64}
  {front_s} {1460.16 8.64}
  {front_c} {1460.16 250.56}
  {front_n} {1460.16 768.96}
}
foreach ot_inst [[ord::get_db_block] getInsts] {
  if {![[$ot_inst getMaster] isBlock]} { continue }
  set n [string map {"\\" ""} [$ot_inst getName]]
  if {[regexp {g_c\[(\d+)\]\.g_p\[(\d+)\]\.(?:genblk\d+\.)?g_t[ew]\.u_t} $n -> c p]} { set k t:$c:$p } \
  elseif {[regexp {g_c\[(\d+)\]\.(?:genblk\d+\.)?g_be_[ew]\.u_be} $n -> c]} { set k b:$c } \
  elseif {[regexp {g_fd\.u_fn} $n]} { set k front_n } elseif {[regexp {g_fd\.u_fc} $n]} { set k front_c } \
  elseif {[regexp {g_fd\.u_fs} $n]} { set k front_s } else { error "no slot for $n" }
  place_macro -macro_name [$ot_inst getName] -location $ot_xy($k) -orientation R0
  incr ot_n
}
if {$ot_n != 27} { error "macro_place: placed $ot_n" }
puts "ot macro_place: $ot_n pieces"
