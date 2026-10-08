set ot_n 0
array set ot_xy {
  {t:0:0} {8.64 613.44}
  {t:0:1} {8.64 95.04}
  {b:0} {30.24 8.64}
  {t:1:0} {380.16 613.44}
  {t:1:1} {380.16 95.04}
  {b:1} {401.76 8.64}
  {t:2:0} {751.68 613.44}
  {t:2:1} {751.68 95.04}
  {b:2} {773.28 8.64}
  {t:3:0} {1123.2 613.44}
  {t:3:1} {1123.2 95.04}
  {b:3} {1144.8 8.64}
  {t:4:0} {1935.36 613.44}
  {t:4:1} {1935.36 95.04}
  {b:4} {1956.96 8.64}
  {t:5:0} {2306.88 613.44}
  {t:5:1} {2306.88 95.04}
  {b:5} {2328.48 8.64}
  {t:6:0} {2678.4 613.44}
  {t:6:1} {2678.4 95.04}
  {b:6} {2700.0 8.64}
  {t:7:0} {3049.92 613.44}
  {t:7:1} {3049.92 95.04}
  {b:7} {3071.52 8.64}
  {front_s} {1494.72 8.64}
  {front_c} {1494.72 250.56}
  {front_n} {1494.72 768.96}
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
