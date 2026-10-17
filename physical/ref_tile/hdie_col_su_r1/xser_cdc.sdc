# hdie_col_su_r1 XSER=1 crossing CDC bounds (HBM-COLSU 2026-10-17; spec "sdc_extra", inlined into clock.sdc and signoff.sdc).
# ot_hbm_static_cfg_collar XSER=1 is a SYNCHRONISED 3:4 boundary (owner: synchronised/elastic boundaries at clock-domain
# edges). Same idiom as the TA15 clock-boundary synchronisers (physical/hbm_accel_die_views/clock_boundary/production_body_cl.sdc):
# a bounded window (max / min 0, -ignore_clock_latency) on exactly three cell groups, every other arc timed with no exception.
#   g_xser.x1_seq*   synchroniser stage 1 of the 2-bit Gray event sequence (from g_xser.h_seq*): 250 / 0 ps
#   g_rst_sync.rs[0] synchroniser stage 1 of the stream-domain reset (from g_rst_sync.rc[1]): 250 / 0 ps
#   g_xser.sh_*      serial shadows of the held payload (from g_xser.h_*): 833 / 0 ps. The RTL consumes a shadow only on
#                    the edge after x2 shows the new code: >= 1111 ps - skew after the publish edge and >= 2222 ps before
#                    the next possible change (events >= 4 stream edges apart); the tb CDC monitor checks that window.
# Why a bound and not flop->flop: clk_in and clk are different die entries (die-skew reserve setup 150 / hold 100 ps between
# them), so a direct arc needs <= 278-150 ps and >= 100 ps + hold at once; r2 (c7a2a833d) measured FF -81.0 ps on all 282
# crossing endpoints with every one hold-ECO infeasible.
set ot_xc_all [get_cells -quiet {g_xser.* g_rst_sync.*}]
if {[llength $ot_xc_all]} {
  set ot_xc_hs [get_cells -quiet {g_xser.h_seq*}]
  set ot_xc_x1 [get_cells -quiet {g_xser.x1_seq*}]
  set ot_xc_h  [get_cells -quiet {g_xser.h_ct* g_xser.h_ca* g_xser.h_cd* g_xser.h_cv* g_xser.h_dv* g_xser.h_lv*}]
  set ot_xc_sh [get_cells -quiet {g_xser.sh_*}]
  set ot_xc_rc [get_cells -quiet {g_rst_sync.rc[1]*}]
  set ot_xc_rs [get_cells -quiet {g_rst_sync.rs[0]*}]
  puts "OT_XSER_CDC h_seq [llength $ot_xc_hs] x1 [llength $ot_xc_x1] h [llength $ot_xc_h] sh [llength $ot_xc_sh] rc1 [llength $ot_xc_rc] rs0 [llength $ot_xc_rs]"
  if {![llength $ot_xc_hs] || ![llength $ot_xc_x1] || ![llength $ot_xc_h] || ![llength $ot_xc_sh] || ![llength $ot_xc_rc] || ![llength $ot_xc_rs]} {
    error "OT_XSER_CDC: crossing cells not found"
  }
  set_max_delay 250 -ignore_clock_latency -from $ot_xc_hs -to $ot_xc_x1
  set_min_delay 0   -ignore_clock_latency -from $ot_xc_hs -to $ot_xc_x1
  set_max_delay 250 -ignore_clock_latency -from $ot_xc_rc -to $ot_xc_rs
  set_min_delay 0   -ignore_clock_latency -from $ot_xc_rc -to $ot_xc_rs
  set_max_delay 833 -ignore_clock_latency -from $ot_xc_h  -to $ot_xc_sh
  set_min_delay 0   -ignore_clock_latency -from $ot_xc_h  -to $ot_xc_sh
}
