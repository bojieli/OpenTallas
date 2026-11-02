# DISABLED candidate exact internal macro sites; fresh normal floorplan only.
set b [ord::get_db_block]
set u [$b getDbUnitsPerMicron]
set targets [dict create \
  {u_q.u_mem.g_b[0].g_w[0].u_m} {ot_sram_1r1w_128x256_m1_r2c2_p192_mir 388.800000 43.200000 R0} \
  {u_q.u_mem.g_b[0].g_w[1].u_m} {ot_sram_1r1w_128x256_m1_r2c2_p192_mir 388.800000 172.800000 R0} \
  {u_q.u_mem.g_b[0].g_w[2].u_m} {ot_sram_1r1w_128x256_m1_r2c2_p192_mir 388.800000 388.800000 R0} \
  {u_q.u_mem.g_b[1].g_w[0].u_m} {ot_sram_1r1w_128x256_m1_r2c2_p192_mir 518.400000 43.200000 R0} \
  {u_q.u_mem.g_b[1].g_w[1].u_m} {ot_sram_1r1w_128x256_m1_r2c2_p192_mir 518.400000 172.800000 R0} \
  {u_q.u_mem.g_b[1].g_w[2].u_m} {ot_sram_1r1w_128x256_m1_r2c2_p192_mir 518.400000 388.800000 R0} \
  {u_q.u_s.u_fq.g_bank[0].u_m} {ot_sram_1r1w_32x128_m1_p192_rc 43.200000 356.400000 R0} \
  {u_q.u_s.u_fq.g_bank[1].u_m} {ot_sram_1r1w_32x128_m1_p192_rc 129.600000 356.400000 R0} \
  {u_q.u_s.u_fq.g_bank[2].u_m} {ot_sram_1r1w_32x128_m1_p192_rc 216.000000 356.400000 R0} \
  {u_q.u_s.u_fq.g_bank[3].u_m} {ot_sram_1r1w_32x128_m1_p192_rc 302.400000 356.400000 R0} \
  {u_q.u_s.u_fq.g_bank[4].u_m} {ot_sram_1r1w_32x128_m1_p192_rc 475.200000 518.400000 R0} \
  {u_q.u_s.u_hc.g_bank[0].u_bank} {ot_s81ph_native_sel_hist_bank 43.200000 110.160000 R0} \
  {u_q.u_s.u_hc.g_bank[1].u_bank} {ot_s81ph_native_sel_hist_bank 129.600000 110.160000 R0} \
  {u_q.u_s.u_hc.g_bank[2].u_bank} {ot_s81ph_native_sel_hist_bank 216.000000 110.160000 R0} \
  {u_q.u_s.u_hc.g_bank[3].u_bank} {ot_s81ph_native_sel_hist_bank 302.400000 110.160000 R0} \
  {u_q.u_s.u_hc.g_bank[4].u_bank} {ot_s81ph_native_sel_hist_bank 43.200000 196.560000 R0} \
  {u_q.u_s.u_hc.g_bank[5].u_bank} {ot_s81ph_native_sel_hist_bank 129.600000 196.560000 R0} \
  {u_q.u_s.u_hc.g_bank[6].u_bank} {ot_s81ph_native_sel_hist_bank 216.000000 196.560000 R0} \
  {u_q.u_s.u_hc.g_bank[7].u_bank} {ot_s81ph_native_sel_hist_bank 302.400000 196.560000 R0} \
  {u_q.u_s.u_hf.g_bank[0].u_bank} {ot_s81ph_native_sel_hist_bank 43.200000 475.200000 R0} \
  {u_q.u_s.u_hf.g_bank[1].u_bank} {ot_s81ph_native_sel_hist_bank 129.600000 475.200000 R0} \
  {u_q.u_s.u_hf.g_bank[2].u_bank} {ot_s81ph_native_sel_hist_bank 216.000000 475.200000 R0} \
  {u_q.u_s.u_hf.g_bank[3].u_bank} {ot_s81ph_native_sel_hist_bank 302.400000 475.200000 R0} \
  {u_q.u_s.u_hf.g_bank[4].u_bank} {ot_s81ph_native_sel_hist_bank 43.200000 561.600000 R0} \
  {u_q.u_s.u_hf.g_bank[5].u_bank} {ot_s81ph_native_sel_hist_bank 129.600000 561.600000 R0} \
  {u_q.u_s.u_hf.g_bank[6].u_bank} {ot_s81ph_native_sel_hist_bank 216.000000 561.600000 R0} \
  {u_q.u_s.u_hf.g_bank[7].u_bank} {ot_s81ph_native_sel_hist_bank 302.400000 561.600000 R0} \
  {u_q.u_s.u_ofq.g_bank[0].u_m} {ot_sram_1r1w_32x128_m1_p192_rc 43.200000 282.960000 R0} \
  {u_q.u_s.u_ofq.g_bank[1].u_m} {ot_sram_1r1w_32x128_m1_p192_rc 129.600000 282.960000 R0} \
  {u_q.u_s.u_ofq.g_bank[2].u_m} {ot_sram_1r1w_32x128_m1_p192_rc 216.000000 282.960000 R0} \
  {u_q.u_s.u_ofq.g_bank[3].u_m} {ot_sram_1r1w_32x128_m1_p192_rc 302.400000 282.960000 R0} \
  {u_q.u_s.u_ofq.g_bank[4].u_m} {ot_sram_1r1w_32x128_m1_p192_rc 388.800000 518.400000 R0} \
]
set hits {}
foreach i [$b getInsts] {
  set n [string map [list [format %c 92] {}] [$i getName]]
  if {![dict exists $targets $n]} continue
  if {[dict exists $hits $n]} {error "duplicate macro $n"}
  lassign [dict get $targets $n] master x y orient
  if {[[$i getMaster] getName] ne $master} {error "macro master mismatch $n"}
  $i setOrient $orient
  $i setLocation [expr {round($x*$u)}] [expr {round($y*$u)}]
  $i setPlacementStatus FIRM
  dict set hits $n 1
}
if {[dict size $hits] !=32} {error "candidate expected32 exact macro instances"}
