# case (a): HBM accelerator die floorplan, macro legality, on-track assert, pin access
proc mem {tag} { set f [open /proc/self/status]; set s [read $f]; close $f
  regexp {VmRSS:\s+(\d+)} $s -> r; puts "OTMEM $tag [expr {$r/1024}] MB [clock seconds]" }
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f {phy.lef serdes.lef ucie.lef elements.lef views.lef} { read_lef /work/$f }
define_corners ss ff
read_liberty -corner ss /work/hfd_attn_tile_ss.lib
read_liberty -corner ff /work/hfd_attn_tile_ff.lib
read_liberty -corner ss /work/hfd_barrier_ss.lib
read_liberty -corner ff /work/hfd_barrier_ff.lib
read_liberty -corner ss /work/hfd_cdist_r14_ss.lib
read_liberty -corner ff /work/hfd_cdist_r14_ff.lib
read_liberty -corner ss /work/hfd_cdist_r15_ss.lib
read_liberty -corner ff /work/hfd_cdist_r15_ff.lib
read_liberty -corner ss /work/hfd_gath_r10_ss.lib
read_liberty -corner ff /work/hfd_gath_r10_ff.lib
read_liberty -corner ss /work/hfd_gath_r24_ss.lib
read_liberty -corner ff /work/hfd_gath_r24_ff.lib
read_liberty -corner ss /work/hfd_gath_r25_ss.lib
read_liberty -corner ff /work/hfd_gath_r25_ff.lib
read_liberty -corner ss /work/hfd_gath_r8_ss.lib
read_liberty -corner ff /work/hfd_gath_r8_ff.lib
read_liberty -corner ss /work/hfd_gath_r9_ss.lib
read_liberty -corner ff /work/hfd_gath_r9_ff.lib
read_liberty -corner ss /work/hfd_index_q_b4_ss.lib
read_liberty -corner ff /work/hfd_index_q_b4_ff.lib
read_liberty -corner ss /work/hfd_mcast_r5_ss.lib
read_liberty -corner ff /work/hfd_mcast_r5_ff.lib
read_liberty -corner ss /work/hfd_mcast_r7_ss.lib
read_liberty -corner ff /work/hfd_mcast_r7_ff.lib
read_liberty -corner ss /work/hfd_meso_r1_ss.lib
read_liberty -corner ff /work/hfd_meso_r1_ff.lib
read_liberty -corner ss /work/hfd_meso_r28_ss.lib
read_liberty -corner ff /work/hfd_meso_r28_ff.lib
read_liberty -corner ss /work/hfd_meso_r32_ss.lib
read_liberty -corner ff /work/hfd_meso_r32_ff.lib
read_liberty -corner ss /work/hfd_meso_r35_ss.lib
read_liberty -corner ff /work/hfd_meso_r35_ff.lib
read_liberty -corner ss /work/hfd_meso_r37_ss.lib
read_liberty -corner ff /work/hfd_meso_r37_ff.lib
read_liberty -corner ss /work/hfd_router_ss.lib
read_liberty -corner ff /work/hfd_router_ff.lib
read_liberty -corner ss /work/hfd_sm_ss.lib
read_liberty -corner ff /work/hfd_sm_ff.lib
read_liberty -corner ss /work/hfd_stn_r0_ss.lib
read_liberty -corner ff /work/hfd_stn_r0_ff.lib
read_liberty -corner ss /work/hfd_stn_r11_ss.lib
read_liberty -corner ff /work/hfd_stn_r11_ff.lib
read_liberty -corner ss /work/hfd_stn_r12_ss.lib
read_liberty -corner ff /work/hfd_stn_r12_ff.lib
read_liberty -corner ss /work/hfd_stn_r13_ss.lib
read_liberty -corner ff /work/hfd_stn_r13_ff.lib
read_liberty -corner ss /work/hfd_stn_r16_ss.lib
read_liberty -corner ff /work/hfd_stn_r16_ff.lib
read_liberty -corner ss /work/hfd_stn_r17_ss.lib
read_liberty -corner ff /work/hfd_stn_r17_ff.lib
read_liberty -corner ss /work/hfd_stn_r18_ss.lib
read_liberty -corner ff /work/hfd_stn_r18_ff.lib
read_liberty -corner ss /work/hfd_stn_r19_ss.lib
read_liberty -corner ff /work/hfd_stn_r19_ff.lib
read_liberty -corner ss /work/hfd_stn_r2_ss.lib
read_liberty -corner ff /work/hfd_stn_r2_ff.lib
read_liberty -corner ss /work/hfd_stn_r20_ss.lib
read_liberty -corner ff /work/hfd_stn_r20_ff.lib
read_liberty -corner ss /work/hfd_stn_r21_ss.lib
read_liberty -corner ff /work/hfd_stn_r21_ff.lib
read_liberty -corner ss /work/hfd_stn_r22_ss.lib
read_liberty -corner ff /work/hfd_stn_r22_ff.lib
read_liberty -corner ss /work/hfd_stn_r23_ss.lib
read_liberty -corner ff /work/hfd_stn_r23_ff.lib
read_liberty -corner ss /work/hfd_stn_r26_ss.lib
read_liberty -corner ff /work/hfd_stn_r26_ff.lib
read_liberty -corner ss /work/hfd_stn_r27_ss.lib
read_liberty -corner ff /work/hfd_stn_r27_ff.lib
read_liberty -corner ss /work/hfd_stn_r29_ss.lib
read_liberty -corner ff /work/hfd_stn_r29_ff.lib
read_liberty -corner ss /work/hfd_stn_r3_ss.lib
read_liberty -corner ff /work/hfd_stn_r3_ff.lib
read_liberty -corner ss /work/hfd_stn_r30_ss.lib
read_liberty -corner ff /work/hfd_stn_r30_ff.lib
read_liberty -corner ss /work/hfd_stn_r31_ss.lib
read_liberty -corner ff /work/hfd_stn_r31_ff.lib
read_liberty -corner ss /work/hfd_stn_r34_ss.lib
read_liberty -corner ff /work/hfd_stn_r34_ff.lib
read_liberty -corner ss /work/hfd_stn_r36_ss.lib
read_liberty -corner ff /work/hfd_stn_r36_ff.lib
read_liberty -corner ss /work/hfd_stn_r4_ss.lib
read_liberty -corner ff /work/hfd_stn_r4_ff.lib
read_liberty -corner ss /work/hfd_svc_SE_s6_ss.lib
read_liberty -corner ff /work/hfd_svc_SE_s6_ff.lib
read_liberty -corner ss /work/hfd_svc_SW_s4_ss.lib
read_liberty -corner ff /work/hfd_svc_SW_s4_ff.lib
read_liberty -corner ss /work/ot_pdie_serdes_ss.lib
read_liberty -corner ff /work/ot_pdie_serdes_ff.lib
read_liberty -corner ss /work/ot_hbm_host_phy_ss.lib
read_liberty -corner ff /work/ot_hbm_host_phy_ff.lib
read_liberty -corner ss /work/ot_hbm3e_phy_v41x_aw30_e8p5_ss.lib
read_liberty -corner ff /work/ot_hbm3e_phy_v41x_aw30_e8p5_ff.lib
read_verilog /work/die.v
link_design hfd_die
initialize_floorplan -die_area {0 0 30590.352 24621.840} -core_area {0 0 30590.352 24621.840} -site asap7sc7p5t
source /OpenROAD-flow-scripts/flow/platforms/asap7/openRoad/make_tracks.tcl
set ::env(MAKE_TRACKS) /OpenROAD-flow-scripts/flow/platforms/asap7/openRoad/make_tracks.tcl
source /work/snap.tcl
source /work/place.tcl

source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set_wire_rc -signal -layer M7
set_wire_rc -clock -layer M7
estimate_parasitics -placement
set_cmd_units -time ns -capacitance fF
# Clock nets are ideal here: data wires retain their actual parasitics.
# The clock plan supplies pin arrival; do not propagate the unrouted clock net.
set ot_clock_missing {}
set ot_clock_bound 0
set ot_bound_names [dict create]
proc ot_clock_pin {name} {
  set inst [lindex [split $name /] 0]
  foreach p [get_pins -quiet "$inst/*"] {
    if {[get_full_name $p] eq $name} { return $p }
  }
  return {}
}
set ot_domain_pins [dict create]
set p [ot_clock_pin {at_NE_21/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_NE_21/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_NE_22/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_NE_22/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_NE_23/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_NE_23/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_NE_31/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_NE_31/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_NE_32/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_NE_32/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_NE_33/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_NE_33/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_NE_01/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_NE_01/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_NE_02/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_NE_02/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_NE_03/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_NE_03/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_NE_11/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_NE_11/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_NE_12/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_NE_12/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_NE_13/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_NE_13/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_NE_00/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_NE_00/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w358_ivp_NE/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w358_ivp_NE/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {hb_index_NE_b5/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_index_NE_b5/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w348_iv_NE/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w348_iv_NE/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_NE_10/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_NE_10/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {hb_index_NE_b4/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_index_NE_b4/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {hb_index_NE_b3/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_index_NE_b3/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_NE_20/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_NE_20/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {hb_index_NE_b2/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_index_NE_b2/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_NE_30/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_NE_30/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {hb_index_NE_b1/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_index_NE_b1/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {hb_index_NE_b0/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_index_NE_b0/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_NW_03/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_NW_03/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w357_ivp_NW/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w357_ivp_NW/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {hb_index_NW_b5/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_index_NW_b5/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w344_iv_NW/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w344_iv_NW/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_NW_13/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_NW_13/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {hb_index_NW_b4/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_index_NW_b4/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {hb_index_NW_b3/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_index_NW_b3/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_NW_23/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_NW_23/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {hb_index_NW_b2/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_index_NW_b2/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_NW_33/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_NW_33/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {hb_index_NW_b1/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_index_NW_b1/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {hb_index_NW_b0/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_index_NW_b0/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_NW_20/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_NW_20/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_NW_21/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_NW_21/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_NW_22/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_NW_22/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_NW_30/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_NW_30/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_NW_31/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_NW_31/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_NW_32/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_NW_32/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_NW_00/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_NW_00/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_NW_01/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_NW_01/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_NW_02/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_NW_02/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_NW_10/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_NW_10/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_NW_11/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_NW_11/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_NW_12/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_NW_12/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_SE_21/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_SE_21/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_SE_22/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_SE_22/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_SE_23/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_SE_23/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_SE_31/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_SE_31/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_SE_32/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_SE_32/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_SE_33/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_SE_33/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_SE_01/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_SE_01/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_SE_02/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_SE_02/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_SE_03/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_SE_03/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_SE_11/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_SE_11/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_SE_12/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_SE_12/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_SE_13/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_SE_13/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {hb_index_SE_b0/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_index_SE_b0/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {hb_index_SE_b1/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_index_SE_b1/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_SE_00/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_SE_00/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {hb_index_SE_b2/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_index_SE_b2/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_SE_10/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_SE_10/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {hb_index_SE_b3/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_index_SE_b3/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {hb_index_SE_b4/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_index_SE_b4/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_SE_20/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_SE_20/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w340_iv_SE/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w340_iv_SE/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {hb_index_SE_b5/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_index_SE_b5/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w356_ivp_SE/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w356_ivp_SE/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_SE_30/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_SE_30/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {hb_index_SW_b0/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_index_SW_b0/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {hb_index_SW_b1/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_index_SW_b1/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_SW_03/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_SW_03/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {hb_index_SW_b2/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_index_SW_b2/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_SW_13/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_SW_13/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {hb_index_SW_b3/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_index_SW_b3/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {hb_index_SW_b4/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_index_SW_b4/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_SW_23/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_SW_23/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w336_iv_SW/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w336_iv_SW/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {hb_index_SW_b5/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_index_SW_b5/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w355_ivp_SW/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w355_ivp_SW/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_SW_33/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_SW_33/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_SW_20/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_SW_20/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_SW_21/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_SW_21/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_SW_22/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_SW_22/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_SW_30/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_SW_30/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_SW_31/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_SW_31/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_SW_32/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_SW_32/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_SW_00/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_SW_00/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_SW_01/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_SW_01/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_SW_02/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_SW_02/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_SW_10/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_SW_10/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_SW_11/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_SW_11/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {at_SW_12/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {at_SW_12/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {hb_vm_sw/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_vm_sw/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {hb_vm_se/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_vm_se/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {hb_vm_nw/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_vm_nw/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {hb_vm_ne/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_vm_ne/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w339_iv_SW/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w339_iv_SW/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w343_iv_SE/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w343_iv_SE/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w347_iv_NW/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w347_iv_NW/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w351_iv_NE/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w351_iv_NE/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w352_vr/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w352_vr/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {hb_loader/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_loader/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {hb_router/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_router/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {hb_cmdproc/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_cmdproc/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {hb_barrier/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_barrier/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w354_vr/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w354_vr/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {sm26/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {sm26/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {sm27/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {sm27/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {sm30/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {sm30/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {sm31/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {sm31/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w223_wl_sm30/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w223_wl_sm30/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w227_wl_sm31/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w227_wl_sm31/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w228_rq_sm31/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w228_rq_sm31/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w237_xmNE2b/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w237_xmNE2b/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w238_xmNE3/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w238_xmNE3/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w242_rgNE2/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w242_rgNE2/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w224_rq_sm30/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w224_rq_sm30/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w259_cdNE0/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w259_cdNE0/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w240_rgNE3/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w240_rgNE3/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {sm24/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {sm24/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {sm25/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {sm25/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {sm28/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {sm28/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {sm29/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {sm29/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w215_wl_sm28/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w215_wl_sm28/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w219_wl_sm29/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w219_wl_sm29/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w220_rq_sm29/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w220_rq_sm29/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w236_xmNE1a/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w236_xmNE1a/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w236_xmNE1b/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w236_xmNE1b/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w239_rgNE0/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w239_rgNE0/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w235_xmNE0/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w235_xmNE0/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w216_rq_sm28/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w216_rq_sm28/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w237_xmNE2a/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w237_xmNE2a/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w241_rgNE1/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w241_rgNE1/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w258_cdNE1/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w258_cdNE1/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {sm18/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {sm18/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {sm19/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {sm19/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {sm22/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {sm22/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {sm23/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {sm23/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w149_wl_sm22/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w149_wl_sm22/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w153_wl_sm23/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w153_wl_sm23/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w154_rq_sm23/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w154_rq_sm23/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w162_xmNW2a/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w162_xmNW2a/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w162_xmNW2b/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w162_xmNW2b/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w163_xmNW1b/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w163_xmNW1b/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w166_rgNW3/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w166_rgNW3/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w150_rq_sm22/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w150_rq_sm22/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w168_rgNW2/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w168_rgNW2/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w161_xmNW3/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w161_xmNW3/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {sm16/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {sm16/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {sm17/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {sm17/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {sm20/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {sm20/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {sm21/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {sm21/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w141_wl_sm20/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w141_wl_sm20/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w145_wl_sm21/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w145_wl_sm21/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w146_rq_sm21/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w146_rq_sm21/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w164_xmNW0/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w164_xmNW0/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w167_rgNW1/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w167_rgNW1/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w165_rgNW0/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w165_rgNW0/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w142_rq_sm20/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w142_rq_sm20/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w183_cdNW0/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w183_cdNW0/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w182_cdNW1/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w182_cdNW1/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w163_xmNW1a/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w163_xmNW1a/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {sm10/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {sm10/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {sm11/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {sm11/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {sm14/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {sm14/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {sm15/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {sm15/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w81_wl_sm14/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w81_wl_sm14/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w85_wl_sm15/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w85_wl_sm15/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w86_rq_sm15/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w86_rq_sm15/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w97_xmSE2b/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w97_xmSE2b/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w98_xmSE3/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w98_xmSE3/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w102_rgSE2/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w102_rgSE2/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w82_rq_sm14/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w82_rq_sm14/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w117_cdSE0/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w117_cdSE0/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w100_rgSE3/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w100_rgSE3/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {sm8/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {sm8/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {sm9/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {sm9/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {sm12/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {sm12/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {sm13/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {sm13/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w73_wl_sm12/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w73_wl_sm12/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w77_wl_sm13/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w77_wl_sm13/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w78_rq_sm13/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w78_rq_sm13/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w96_xmSE1a/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w96_xmSE1a/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w96_xmSE1b/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w96_xmSE1b/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w99_rgSE0/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w99_rgSE0/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w95_xmSE0/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w95_xmSE0/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w74_rq_sm12/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w74_rq_sm12/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w97_xmSE2a/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w97_xmSE2a/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w101_rgSE1/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w101_rgSE1/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w116_cdSE1/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w116_cdSE1/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {sm2/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {sm2/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {sm3/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {sm3/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {sm6/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {sm6/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {sm7/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {sm7/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w10_wl_sm6/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w10_wl_sm6/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w14_wl_sm7/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w14_wl_sm7/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w15_rq_sm7/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w15_rq_sm7/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w25_xmSW2a/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w25_xmSW2a/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w25_xmSW2b/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w25_xmSW2b/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w26_xmSW1b/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w26_xmSW1b/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w29_rgSW3/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w29_rgSW3/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w11_rq_sm6/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w11_rq_sm6/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w31_rgSW2/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w31_rgSW2/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w24_xmSW3/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w24_xmSW3/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {sm0/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {sm0/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {sm1/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {sm1/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {sm4/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {sm4/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {sm5/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {sm5/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w2_wl_sm4/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w2_wl_sm4/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w6_wl_sm5/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w6_wl_sm5/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w7_rq_sm5/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w7_rq_sm5/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w27_xmSW0/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w27_xmSW0/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w30_rgSW1/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w30_rgSW1/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w28_rgSW0/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w28_rgSW0/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w3_rq_sm4/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w3_rq_sm4/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w44_cdSW0/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w44_cdSW0/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w43_cdSW1/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w43_cdSW1/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {w26_xmSW1a/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w26_xmSW1a/ck[0]} } else { dict lappend ot_domain_pins clk_stream $p }
set p [ot_clock_pin {hb_sfu_NE/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_sfu_NE/ck[0]} } else { dict lappend ot_domain_pins clk_serial $p }
set p [ot_clock_pin {hb_hc_NE/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_hc_NE/ck[0]} } else { dict lappend ot_domain_pins clk_serial $p }
set p [ot_clock_pin {hb_sfu_SE/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_sfu_SE/ck[0]} } else { dict lappend ot_domain_pins clk_serial $p }
set p [ot_clock_pin {hb_hc_SE/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_hc_SE/ck[0]} } else { dict lappend ot_domain_pins clk_serial $p }
set p [ot_clock_pin {hb_su_SE/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_su_SE/ck[0]} } else { dict lappend ot_domain_pins clk_serial $p }
set p [ot_clock_pin {hb_su_NE/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_su_NE/ck[0]} } else { dict lappend ot_domain_pins clk_serial $p }
set p [ot_clock_pin {hb_hc_NW/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_hc_NW/ck[0]} } else { dict lappend ot_domain_pins clk_serial $p }
set p [ot_clock_pin {hb_sfu_NW/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_sfu_NW/ck[0]} } else { dict lappend ot_domain_pins clk_serial $p }
set p [ot_clock_pin {hb_su_NW/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_su_NW/ck[0]} } else { dict lappend ot_domain_pins clk_serial $p }
set p [ot_clock_pin {hb_su_full/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_su_full/ck[0]} } else { dict lappend ot_domain_pins clk_serial $p }
set p [ot_clock_pin {hb_quant/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_quant/ck[0]} } else { dict lappend ot_domain_pins clk_serial $p }
set p [ot_clock_pin {hb_su_red/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_su_red/ck[0]} } else { dict lappend ot_domain_pins clk_serial $p }
set p [ot_clock_pin {hb_hc_SW/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_hc_SW/ck[0]} } else { dict lappend ot_domain_pins clk_serial $p }
set p [ot_clock_pin {hb_sfu_SW/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_sfu_SW/ck[0]} } else { dict lappend ot_domain_pins clk_serial $p }
set p [ot_clock_pin {hb_su_SW/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {hb_su_SW/ck[0]} } else { dict lappend ot_domain_pins clk_serial $p }
set p [ot_clock_pin {svc_NE_s4/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {svc_NE_s4/ck[0]} } else { dict lappend ot_domain_pins clk_hbm $p }
set p [ot_clock_pin {svc_NE_s5/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {svc_NE_s5/ck[0]} } else { dict lappend ot_domain_pins clk_hbm $p }
set p [ot_clock_pin {svc_NE_s6/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {svc_NE_s6/ck[0]} } else { dict lappend ot_domain_pins clk_hbm $p }
set p [ot_clock_pin {svc_NE_s7/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {svc_NE_s7/ck[0]} } else { dict lappend ot_domain_pins clk_hbm $p }
set p [ot_clock_pin {svc_NE_s8/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {svc_NE_s8/ck[0]} } else { dict lappend ot_domain_pins clk_hbm $p }
set p [ot_clock_pin {svc_NE_s0/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {svc_NE_s0/ck[0]} } else { dict lappend ot_domain_pins clk_hbm $p }
set p [ot_clock_pin {svc_NE_s1/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {svc_NE_s1/ck[0]} } else { dict lappend ot_domain_pins clk_hbm $p }
set p [ot_clock_pin {svc_NE_s2/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {svc_NE_s2/ck[0]} } else { dict lappend ot_domain_pins clk_hbm $p }
set p [ot_clock_pin {svc_NE_s3/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {svc_NE_s3/ck[0]} } else { dict lappend ot_domain_pins clk_hbm $p }
set p [ot_clock_pin {svc_NW_s4/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {svc_NW_s4/ck[0]} } else { dict lappend ot_domain_pins clk_hbm $p }
set p [ot_clock_pin {svc_NW_s5/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {svc_NW_s5/ck[0]} } else { dict lappend ot_domain_pins clk_hbm $p }
set p [ot_clock_pin {svc_NW_s6/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {svc_NW_s6/ck[0]} } else { dict lappend ot_domain_pins clk_hbm $p }
set p [ot_clock_pin {svc_NW_s7/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {svc_NW_s7/ck[0]} } else { dict lappend ot_domain_pins clk_hbm $p }
set p [ot_clock_pin {svc_NW_s0/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {svc_NW_s0/ck[0]} } else { dict lappend ot_domain_pins clk_hbm $p }
set p [ot_clock_pin {svc_NW_s1/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {svc_NW_s1/ck[0]} } else { dict lappend ot_domain_pins clk_hbm $p }
set p [ot_clock_pin {svc_NW_s2/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {svc_NW_s2/ck[0]} } else { dict lappend ot_domain_pins clk_hbm $p }
set p [ot_clock_pin {svc_NW_s3/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {svc_NW_s3/ck[0]} } else { dict lappend ot_domain_pins clk_hbm $p }
set p [ot_clock_pin {svc_SE_s4/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {svc_SE_s4/ck[0]} } else { dict lappend ot_domain_pins clk_hbm $p }
set p [ot_clock_pin {svc_SE_s5/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {svc_SE_s5/ck[0]} } else { dict lappend ot_domain_pins clk_hbm $p }
set p [ot_clock_pin {svc_SE_s6/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {svc_SE_s6/ck[0]} } else { dict lappend ot_domain_pins clk_hbm $p }
set p [ot_clock_pin {svc_SE_s7/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {svc_SE_s7/ck[0]} } else { dict lappend ot_domain_pins clk_hbm $p }
set p [ot_clock_pin {svc_SE_s8/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {svc_SE_s8/ck[0]} } else { dict lappend ot_domain_pins clk_hbm $p }
set p [ot_clock_pin {svc_SE_s0/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {svc_SE_s0/ck[0]} } else { dict lappend ot_domain_pins clk_hbm $p }
set p [ot_clock_pin {svc_SE_s1/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {svc_SE_s1/ck[0]} } else { dict lappend ot_domain_pins clk_hbm $p }
set p [ot_clock_pin {svc_SE_s2/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {svc_SE_s2/ck[0]} } else { dict lappend ot_domain_pins clk_hbm $p }
set p [ot_clock_pin {svc_SE_s3/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {svc_SE_s3/ck[0]} } else { dict lappend ot_domain_pins clk_hbm $p }
set p [ot_clock_pin {svc_SW_s4/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {svc_SW_s4/ck[0]} } else { dict lappend ot_domain_pins clk_hbm $p }
set p [ot_clock_pin {svc_SW_s5/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {svc_SW_s5/ck[0]} } else { dict lappend ot_domain_pins clk_hbm $p }
set p [ot_clock_pin {svc_SW_s6/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {svc_SW_s6/ck[0]} } else { dict lappend ot_domain_pins clk_hbm $p }
set p [ot_clock_pin {svc_SW_s7/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {svc_SW_s7/ck[0]} } else { dict lappend ot_domain_pins clk_hbm $p }
set p [ot_clock_pin {svc_SW_s0/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {svc_SW_s0/ck[0]} } else { dict lappend ot_domain_pins clk_hbm $p }
set p [ot_clock_pin {svc_SW_s1/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {svc_SW_s1/ck[0]} } else { dict lappend ot_domain_pins clk_hbm $p }
set p [ot_clock_pin {svc_SW_s2/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {svc_SW_s2/ck[0]} } else { dict lappend ot_domain_pins clk_hbm $p }
set p [ot_clock_pin {svc_SW_s3/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {svc_SW_s3/ck[0]} } else { dict lappend ot_domain_pins clk_hbm $p }
set p [ot_clock_pin {w335_host/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w335_host/ck[0]} } else { dict lappend ot_domain_pins clk_link $p }
set p [ot_clock_pin {lk_host/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {lk_host/ck[0]} } else { dict lappend ot_domain_pins clk_link $p }
set p [ot_clock_pin {w310_lk_lk_N0/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w310_lk_lk_N0/ck[0]} } else { dict lappend ot_domain_pins clk_link $p }
set p [ot_clock_pin {w315_lk_lk_N1/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w315_lk_lk_N1/ck[0]} } else { dict lappend ot_domain_pins clk_link $p }
set p [ot_clock_pin {lk_N0/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {lk_N0/ck[0]} } else { dict lappend ot_domain_pins clk_link $p }
set p [ot_clock_pin {lk_N1/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {lk_N1/ck[0]} } else { dict lappend ot_domain_pins clk_link $p }
set p [ot_clock_pin {lk_N2/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {lk_N2/ck[0]} } else { dict lappend ot_domain_pins clk_link $p }
set p [ot_clock_pin {w319_lk_lk_N2/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w319_lk_lk_N2/ck[0]} } else { dict lappend ot_domain_pins clk_link $p }
set p [ot_clock_pin {lk_N3/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {lk_N3/ck[0]} } else { dict lappend ot_domain_pins clk_link $p }
set p [ot_clock_pin {w323_lk_lk_N3/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w323_lk_lk_N3/ck[0]} } else { dict lappend ot_domain_pins clk_link $p }
set p [ot_clock_pin {lk_S0/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {lk_S0/ck[0]} } else { dict lappend ot_domain_pins clk_link $p }
set p [ot_clock_pin {lk_S1/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {lk_S1/ck[0]} } else { dict lappend ot_domain_pins clk_link $p }
set p [ot_clock_pin {lk_S2/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {lk_S2/ck[0]} } else { dict lappend ot_domain_pins clk_link $p }
set p [ot_clock_pin {w289_lk_lk_S0/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w289_lk_lk_S0/ck[0]} } else { dict lappend ot_domain_pins clk_link $p }
set p [ot_clock_pin {w293_lk_lk_S1/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w293_lk_lk_S1/ck[0]} } else { dict lappend ot_domain_pins clk_link $p }
set p [ot_clock_pin {lk_S3/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {lk_S3/ck[0]} } else { dict lappend ot_domain_pins clk_link $p }
set p [ot_clock_pin {lk_S4/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {lk_S4/ck[0]} } else { dict lappend ot_domain_pins clk_link $p }
set p [ot_clock_pin {w298_lk_lk_S2/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w298_lk_lk_S2/ck[0]} } else { dict lappend ot_domain_pins clk_link $p }
set p [ot_clock_pin {w302_lk_lk_S3/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w302_lk_lk_S3/ck[0]} } else { dict lappend ot_domain_pins clk_link $p }
set p [ot_clock_pin {w306_lk_lk_S4/ck[0]}]
if {![llength $p]} { lappend ot_clock_missing {w306_lk_lk_S4/ck[0]} } else { dict lappend ot_domain_pins clk_link $p }
if {[dict exists $ot_domain_pins clk_stream]} {
  create_clock -name clk_stream -period 0.833333000 [dict get $ot_domain_pins clk_stream]
}
if {[dict exists $ot_domain_pins clk_serial]} {
  create_clock -name clk_serial -period 1.111111000 [dict get $ot_domain_pins clk_serial]
}
if {[dict exists $ot_domain_pins clk_hbm]} {
  create_clock -name clk_hbm -period 1.024000000 [dict get $ot_domain_pins clk_hbm]
}
if {[dict exists $ot_domain_pins clk_link]} {
  create_clock -name clk_link -period 0.833333000 [dict get $ot_domain_pins clk_link]
}
set p [ot_clock_pin {at_NE_21/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.679100000 $p; dict set ot_bound_names {at_NE_21/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_NE_22/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.679100000 $p; dict set ot_bound_names {at_NE_22/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_NE_23/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.679100000 $p; dict set ot_bound_names {at_NE_23/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_NE_31/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.679100000 $p; dict set ot_bound_names {at_NE_31/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_NE_32/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.679100000 $p; dict set ot_bound_names {at_NE_32/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_NE_33/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.679100000 $p; dict set ot_bound_names {at_NE_33/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_NE_01/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.678600000 $p; dict set ot_bound_names {at_NE_01/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_NE_02/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.678600000 $p; dict set ot_bound_names {at_NE_02/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_NE_03/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.678600000 $p; dict set ot_bound_names {at_NE_03/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_NE_11/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.678600000 $p; dict set ot_bound_names {at_NE_11/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_NE_12/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.678600000 $p; dict set ot_bound_names {at_NE_12/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_NE_13/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.678600000 $p; dict set ot_bound_names {at_NE_13/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_NE_00/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.103100000 $p; dict set ot_bound_names {at_NE_00/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w358_ivp_NE/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.525800000 $p; dict set ot_bound_names {w358_ivp_NE/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_index_NE_b5/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.679100000 $p; dict set ot_bound_names {hb_index_NE_b5/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w348_iv_NE/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.525300000 $p; dict set ot_bound_names {w348_iv_NE/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_NE_10/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.103100000 $p; dict set ot_bound_names {at_NE_10/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_index_NE_b4/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.103100000 $p; dict set ot_bound_names {hb_index_NE_b4/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_index_NE_b3/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.818100000 $p; dict set ot_bound_names {hb_index_NE_b3/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_NE_20/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.103100000 $p; dict set ot_bound_names {at_NE_20/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_index_NE_b2/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.694100000 $p; dict set ot_bound_names {hb_index_NE_b2/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_NE_30/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.103100000 $p; dict set ot_bound_names {at_NE_30/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_index_NE_b1/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.871100000 $p; dict set ot_bound_names {hb_index_NE_b1/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_index_NE_b0/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.817100000 $p; dict set ot_bound_names {hb_index_NE_b0/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_NW_03/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.105000000 $p; dict set ot_bound_names {at_NW_03/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w357_ivp_NW/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.527700000 $p; dict set ot_bound_names {w357_ivp_NW/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_index_NW_b5/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.681000000 $p; dict set ot_bound_names {hb_index_NW_b5/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w344_iv_NW/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.527200000 $p; dict set ot_bound_names {w344_iv_NW/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_NW_13/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.105000000 $p; dict set ot_bound_names {at_NW_13/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_index_NW_b4/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.105000000 $p; dict set ot_bound_names {hb_index_NW_b4/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_index_NW_b3/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.820000000 $p; dict set ot_bound_names {hb_index_NW_b3/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_NW_23/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.105000000 $p; dict set ot_bound_names {at_NW_23/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_index_NW_b2/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.696000000 $p; dict set ot_bound_names {hb_index_NW_b2/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_NW_33/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.105000000 $p; dict set ot_bound_names {at_NW_33/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_index_NW_b1/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.873000000 $p; dict set ot_bound_names {hb_index_NW_b1/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_index_NW_b0/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.819000000 $p; dict set ot_bound_names {hb_index_NW_b0/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_NW_20/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.681000000 $p; dict set ot_bound_names {at_NW_20/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_NW_21/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.681000000 $p; dict set ot_bound_names {at_NW_21/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_NW_22/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.681000000 $p; dict set ot_bound_names {at_NW_22/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_NW_30/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.681000000 $p; dict set ot_bound_names {at_NW_30/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_NW_31/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.681000000 $p; dict set ot_bound_names {at_NW_31/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_NW_32/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.681000000 $p; dict set ot_bound_names {at_NW_32/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_NW_00/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.681000000 $p; dict set ot_bound_names {at_NW_00/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_NW_01/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.681000000 $p; dict set ot_bound_names {at_NW_01/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_NW_02/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.681000000 $p; dict set ot_bound_names {at_NW_02/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_NW_10/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.681000000 $p; dict set ot_bound_names {at_NW_10/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_NW_11/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.681000000 $p; dict set ot_bound_names {at_NW_11/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_NW_12/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.681000000 $p; dict set ot_bound_names {at_NW_12/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_SE_21/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.679100000 $p; dict set ot_bound_names {at_SE_21/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_SE_22/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.679100000 $p; dict set ot_bound_names {at_SE_22/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_SE_23/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.679100000 $p; dict set ot_bound_names {at_SE_23/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_SE_31/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.679100000 $p; dict set ot_bound_names {at_SE_31/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_SE_32/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.679100000 $p; dict set ot_bound_names {at_SE_32/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_SE_33/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.679100000 $p; dict set ot_bound_names {at_SE_33/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_SE_01/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.679100000 $p; dict set ot_bound_names {at_SE_01/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_SE_02/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.679100000 $p; dict set ot_bound_names {at_SE_02/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_SE_03/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.679100000 $p; dict set ot_bound_names {at_SE_03/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_SE_11/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.679100000 $p; dict set ot_bound_names {at_SE_11/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_SE_12/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.679100000 $p; dict set ot_bound_names {at_SE_12/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_SE_13/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.679100000 $p; dict set ot_bound_names {at_SE_13/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_index_SE_b0/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.815200000 $p; dict set ot_bound_names {hb_index_SE_b0/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_index_SE_b1/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.869200000 $p; dict set ot_bound_names {hb_index_SE_b1/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_SE_00/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.101200000 $p; dict set ot_bound_names {at_SE_00/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_index_SE_b2/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.692200000 $p; dict set ot_bound_names {hb_index_SE_b2/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_SE_10/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.101200000 $p; dict set ot_bound_names {at_SE_10/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_index_SE_b3/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.816200000 $p; dict set ot_bound_names {hb_index_SE_b3/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_index_SE_b4/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.101200000 $p; dict set ot_bound_names {hb_index_SE_b4/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_SE_20/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.101200000 $p; dict set ot_bound_names {at_SE_20/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w340_iv_SE/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.523400000 $p; dict set ot_bound_names {w340_iv_SE/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_index_SE_b5/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.677200000 $p; dict set ot_bound_names {hb_index_SE_b5/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w356_ivp_SE/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.523900000 $p; dict set ot_bound_names {w356_ivp_SE/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_SE_30/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.101200000 $p; dict set ot_bound_names {at_SE_30/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_index_SW_b0/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.817100000 $p; dict set ot_bound_names {hb_index_SW_b0/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_index_SW_b1/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.871100000 $p; dict set ot_bound_names {hb_index_SW_b1/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_SW_03/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.103100000 $p; dict set ot_bound_names {at_SW_03/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_index_SW_b2/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.694100000 $p; dict set ot_bound_names {hb_index_SW_b2/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_SW_13/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.103100000 $p; dict set ot_bound_names {at_SW_13/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_index_SW_b3/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.818100000 $p; dict set ot_bound_names {hb_index_SW_b3/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_index_SW_b4/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.103100000 $p; dict set ot_bound_names {hb_index_SW_b4/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_SW_23/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.103100000 $p; dict set ot_bound_names {at_SW_23/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w336_iv_SW/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.525300000 $p; dict set ot_bound_names {w336_iv_SW/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_index_SW_b5/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.679100000 $p; dict set ot_bound_names {hb_index_SW_b5/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w355_ivp_SW/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.525800000 $p; dict set ot_bound_names {w355_ivp_SW/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_SW_33/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.103100000 $p; dict set ot_bound_names {at_SW_33/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_SW_20/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.681000000 $p; dict set ot_bound_names {at_SW_20/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_SW_21/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.681000000 $p; dict set ot_bound_names {at_SW_21/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_SW_22/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.681000000 $p; dict set ot_bound_names {at_SW_22/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_SW_30/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.681000000 $p; dict set ot_bound_names {at_SW_30/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_SW_31/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.681000000 $p; dict set ot_bound_names {at_SW_31/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_SW_32/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.681000000 $p; dict set ot_bound_names {at_SW_32/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_SW_00/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.681000000 $p; dict set ot_bound_names {at_SW_00/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_SW_01/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.681000000 $p; dict set ot_bound_names {at_SW_01/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_SW_02/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.681000000 $p; dict set ot_bound_names {at_SW_02/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_SW_10/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.681000000 $p; dict set ot_bound_names {at_SW_10/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_SW_11/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.681000000 $p; dict set ot_bound_names {at_SW_11/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {at_SW_12/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.681000000 $p; dict set ot_bound_names {at_SW_12/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_vm_sw/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.678100000 $p; dict set ot_bound_names {hb_vm_sw/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_vm_se/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.678100000 $p; dict set ot_bound_names {hb_vm_se/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_vm_nw/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.678100000 $p; dict set ot_bound_names {hb_vm_nw/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_vm_ne/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.678100000 $p; dict set ot_bound_names {hb_vm_ne/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w339_iv_SW/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.056600000 $p; dict set ot_bound_names {w339_iv_SW/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w343_iv_SE/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.056600000 $p; dict set ot_bound_names {w343_iv_SE/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w347_iv_NW/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.056600000 $p; dict set ot_bound_names {w347_iv_NW/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w351_iv_NE/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.056600000 $p; dict set ot_bound_names {w351_iv_NE/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w352_vr/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.100300000 $p; dict set ot_bound_names {w352_vr/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_loader/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.679200000 $p; dict set ot_bound_names {hb_loader/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_router/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.679200000 $p; dict set ot_bound_names {hb_router/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_cmdproc/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.679200000 $p; dict set ot_bound_names {hb_cmdproc/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_barrier/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.953200000 $p; dict set ot_bound_names {hb_barrier/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w354_vr/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.058200000 $p; dict set ot_bound_names {w354_vr/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {sm26/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.678900000 $p; dict set ot_bound_names {sm26/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {sm27/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.678900000 $p; dict set ot_bound_names {sm27/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {sm30/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.678900000 $p; dict set ot_bound_names {sm30/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {sm31/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.678900000 $p; dict set ot_bound_names {sm31/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w223_wl_sm30/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.003200000 $p; dict set ot_bound_names {w223_wl_sm30/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w227_wl_sm31/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.003200000 $p; dict set ot_bound_names {w227_wl_sm31/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w228_rq_sm31/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.109400000 $p; dict set ot_bound_names {w228_rq_sm31/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w237_xmNE2b/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.943300000 $p; dict set ot_bound_names {w237_xmNE2b/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w238_xmNE3/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.943300000 $p; dict set ot_bound_names {w238_xmNE3/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w242_rgNE2/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.950600000 $p; dict set ot_bound_names {w242_rgNE2/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w224_rq_sm30/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.109400000 $p; dict set ot_bound_names {w224_rq_sm30/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w259_cdNE0/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.047400000 $p; dict set ot_bound_names {w259_cdNE0/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w240_rgNE3/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.078300000 $p; dict set ot_bound_names {w240_rgNE3/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {sm24/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.678400000 $p; dict set ot_bound_names {sm24/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {sm25/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.678400000 $p; dict set ot_bound_names {sm25/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {sm28/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.678400000 $p; dict set ot_bound_names {sm28/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {sm29/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.678400000 $p; dict set ot_bound_names {sm29/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w215_wl_sm28/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.002700000 $p; dict set ot_bound_names {w215_wl_sm28/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w219_wl_sm29/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.002700000 $p; dict set ot_bound_names {w219_wl_sm29/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w220_rq_sm29/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.108900000 $p; dict set ot_bound_names {w220_rq_sm29/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w236_xmNE1a/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.942800000 $p; dict set ot_bound_names {w236_xmNE1a/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w236_xmNE1b/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.942800000 $p; dict set ot_bound_names {w236_xmNE1b/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w239_rgNE0/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.077800000 $p; dict set ot_bound_names {w239_rgNE0/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w235_xmNE0/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.875900000 $p; dict set ot_bound_names {w235_xmNE0/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w216_rq_sm28/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.108900000 $p; dict set ot_bound_names {w216_rq_sm28/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w237_xmNE2a/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.942800000 $p; dict set ot_bound_names {w237_xmNE2a/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w241_rgNE1/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.053300000 $p; dict set ot_bound_names {w241_rgNE1/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w258_cdNE1/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.014500000 $p; dict set ot_bound_names {w258_cdNE1/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {sm18/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.680500000 $p; dict set ot_bound_names {sm18/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {sm19/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.680500000 $p; dict set ot_bound_names {sm19/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {sm22/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.680500000 $p; dict set ot_bound_names {sm22/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {sm23/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.680500000 $p; dict set ot_bound_names {sm23/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w149_wl_sm22/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.004800000 $p; dict set ot_bound_names {w149_wl_sm22/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w153_wl_sm23/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.004800000 $p; dict set ot_bound_names {w153_wl_sm23/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w154_rq_sm23/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.111000000 $p; dict set ot_bound_names {w154_rq_sm23/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w162_xmNW2a/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.944900000 $p; dict set ot_bound_names {w162_xmNW2a/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w162_xmNW2b/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.944900000 $p; dict set ot_bound_names {w162_xmNW2b/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w163_xmNW1b/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.944900000 $p; dict set ot_bound_names {w163_xmNW1b/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w166_rgNW3/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.079900000 $p; dict set ot_bound_names {w166_rgNW3/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w150_rq_sm22/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.111000000 $p; dict set ot_bound_names {w150_rq_sm22/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w168_rgNW2/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.952200000 $p; dict set ot_bound_names {w168_rgNW2/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w161_xmNW3/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.878000000 $p; dict set ot_bound_names {w161_xmNW3/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {sm16/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.682400000 $p; dict set ot_bound_names {sm16/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {sm17/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.682400000 $p; dict set ot_bound_names {sm17/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {sm20/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.682400000 $p; dict set ot_bound_names {sm20/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {sm21/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.682400000 $p; dict set ot_bound_names {sm21/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w141_wl_sm20/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.006700000 $p; dict set ot_bound_names {w141_wl_sm20/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w145_wl_sm21/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.006700000 $p; dict set ot_bound_names {w145_wl_sm21/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w146_rq_sm21/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.112900000 $p; dict set ot_bound_names {w146_rq_sm21/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w164_xmNW0/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.946800000 $p; dict set ot_bound_names {w164_xmNW0/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w167_rgNW1/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.057300000 $p; dict set ot_bound_names {w167_rgNW1/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w165_rgNW0/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.081800000 $p; dict set ot_bound_names {w165_rgNW0/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w142_rq_sm20/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.112900000 $p; dict set ot_bound_names {w142_rq_sm20/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w183_cdNW0/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.050900000 $p; dict set ot_bound_names {w183_cdNW0/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w182_cdNW1/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.018500000 $p; dict set ot_bound_names {w182_cdNW1/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w163_xmNW1a/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.946800000 $p; dict set ot_bound_names {w163_xmNW1a/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {sm10/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.678900000 $p; dict set ot_bound_names {sm10/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {sm11/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.678900000 $p; dict set ot_bound_names {sm11/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {sm14/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.678900000 $p; dict set ot_bound_names {sm14/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {sm15/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.678900000 $p; dict set ot_bound_names {sm15/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w81_wl_sm14/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.003200000 $p; dict set ot_bound_names {w81_wl_sm14/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w85_wl_sm15/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.003200000 $p; dict set ot_bound_names {w85_wl_sm15/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w86_rq_sm15/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.109400000 $p; dict set ot_bound_names {w86_rq_sm15/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w97_xmSE2b/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.943300000 $p; dict set ot_bound_names {w97_xmSE2b/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w98_xmSE3/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.943300000 $p; dict set ot_bound_names {w98_xmSE3/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w102_rgSE2/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.950600000 $p; dict set ot_bound_names {w102_rgSE2/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w82_rq_sm14/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.109400000 $p; dict set ot_bound_names {w82_rq_sm14/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w117_cdSE0/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.047400000 $p; dict set ot_bound_names {w117_cdSE0/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w100_rgSE3/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.078300000 $p; dict set ot_bound_names {w100_rgSE3/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {sm8/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.678400000 $p; dict set ot_bound_names {sm8/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {sm9/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.678400000 $p; dict set ot_bound_names {sm9/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {sm12/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.678400000 $p; dict set ot_bound_names {sm12/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {sm13/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.678400000 $p; dict set ot_bound_names {sm13/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w73_wl_sm12/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.002700000 $p; dict set ot_bound_names {w73_wl_sm12/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w77_wl_sm13/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.002700000 $p; dict set ot_bound_names {w77_wl_sm13/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w78_rq_sm13/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.108900000 $p; dict set ot_bound_names {w78_rq_sm13/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w96_xmSE1a/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.942800000 $p; dict set ot_bound_names {w96_xmSE1a/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w96_xmSE1b/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.942800000 $p; dict set ot_bound_names {w96_xmSE1b/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w99_rgSE0/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.077800000 $p; dict set ot_bound_names {w99_rgSE0/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w95_xmSE0/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.875900000 $p; dict set ot_bound_names {w95_xmSE0/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w74_rq_sm12/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.108900000 $p; dict set ot_bound_names {w74_rq_sm12/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w97_xmSE2a/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.942800000 $p; dict set ot_bound_names {w97_xmSE2a/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w101_rgSE1/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.053300000 $p; dict set ot_bound_names {w101_rgSE1/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w116_cdSE1/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.014500000 $p; dict set ot_bound_names {w116_cdSE1/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {sm2/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.680500000 $p; dict set ot_bound_names {sm2/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {sm3/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.680500000 $p; dict set ot_bound_names {sm3/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {sm6/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.680500000 $p; dict set ot_bound_names {sm6/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {sm7/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.680500000 $p; dict set ot_bound_names {sm7/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w10_wl_sm6/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.004800000 $p; dict set ot_bound_names {w10_wl_sm6/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w14_wl_sm7/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.004800000 $p; dict set ot_bound_names {w14_wl_sm7/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w15_rq_sm7/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.111000000 $p; dict set ot_bound_names {w15_rq_sm7/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w25_xmSW2a/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.944900000 $p; dict set ot_bound_names {w25_xmSW2a/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w25_xmSW2b/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.944900000 $p; dict set ot_bound_names {w25_xmSW2b/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w26_xmSW1b/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.944900000 $p; dict set ot_bound_names {w26_xmSW1b/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w29_rgSW3/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.079900000 $p; dict set ot_bound_names {w29_rgSW3/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w11_rq_sm6/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.111000000 $p; dict set ot_bound_names {w11_rq_sm6/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w31_rgSW2/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.952200000 $p; dict set ot_bound_names {w31_rgSW2/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w24_xmSW3/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.878000000 $p; dict set ot_bound_names {w24_xmSW3/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {sm0/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.682400000 $p; dict set ot_bound_names {sm0/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {sm1/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.682400000 $p; dict set ot_bound_names {sm1/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {sm4/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.682400000 $p; dict set ot_bound_names {sm4/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {sm5/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.682400000 $p; dict set ot_bound_names {sm5/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w2_wl_sm4/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.006700000 $p; dict set ot_bound_names {w2_wl_sm4/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w6_wl_sm5/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.006700000 $p; dict set ot_bound_names {w6_wl_sm5/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w7_rq_sm5/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.112900000 $p; dict set ot_bound_names {w7_rq_sm5/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w27_xmSW0/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.946800000 $p; dict set ot_bound_names {w27_xmSW0/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w30_rgSW1/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.057300000 $p; dict set ot_bound_names {w30_rgSW1/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w28_rgSW0/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.081800000 $p; dict set ot_bound_names {w28_rgSW0/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w3_rq_sm4/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.112900000 $p; dict set ot_bound_names {w3_rq_sm4/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w44_cdSW0/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.050900000 $p; dict set ot_bound_names {w44_cdSW0/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w43_cdSW1/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 3.018500000 $p; dict set ot_bound_names {w43_cdSW1/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w26_xmSW1a/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_stream 2.946800000 $p; dict set ot_bound_names {w26_xmSW1a/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_sfu_NE/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_serial 0.843300000 $p; dict set ot_bound_names {hb_sfu_NE/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_hc_NE/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_serial 0.843300000 $p; dict set ot_bound_names {hb_hc_NE/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_sfu_SE/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_serial 0.843300000 $p; dict set ot_bound_names {hb_sfu_SE/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_hc_SE/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_serial 0.843300000 $p; dict set ot_bound_names {hb_hc_SE/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_su_SE/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_serial 0.843300000 $p; dict set ot_bound_names {hb_su_SE/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_su_NE/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_serial 0.843300000 $p; dict set ot_bound_names {hb_su_NE/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_hc_NW/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_serial 0.843400000 $p; dict set ot_bound_names {hb_hc_NW/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_sfu_NW/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_serial 0.843400000 $p; dict set ot_bound_names {hb_sfu_NW/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_su_NW/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_serial 0.843400000 $p; dict set ot_bound_names {hb_su_NW/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_su_full/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_serial 1.013400000 $p; dict set ot_bound_names {hb_su_full/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_quant/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_serial 0.843400000 $p; dict set ot_bound_names {hb_quant/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_su_red/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_serial 0.843400000 $p; dict set ot_bound_names {hb_su_red/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_hc_SW/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_serial 0.844000000 $p; dict set ot_bound_names {hb_hc_SW/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_sfu_SW/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_serial 0.844000000 $p; dict set ot_bound_names {hb_sfu_SW/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {hb_su_SW/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_serial 0.844000000 $p; dict set ot_bound_names {hb_su_SW/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {svc_NE_s4/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_hbm 1.894900000 $p; dict set ot_bound_names {svc_NE_s4/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {svc_NE_s5/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_hbm 1.873900000 $p; dict set ot_bound_names {svc_NE_s5/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {svc_NE_s6/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_hbm 2.140900000 $p; dict set ot_bound_names {svc_NE_s6/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {svc_NE_s7/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_hbm 2.071900000 $p; dict set ot_bound_names {svc_NE_s7/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {svc_NE_s8/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_hbm 1.994400000 $p; dict set ot_bound_names {svc_NE_s8/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {svc_NE_s0/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_hbm 1.890600000 $p; dict set ot_bound_names {svc_NE_s0/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {svc_NE_s1/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_hbm 2.008300000 $p; dict set ot_bound_names {svc_NE_s1/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {svc_NE_s2/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_hbm 2.189600000 $p; dict set ot_bound_names {svc_NE_s2/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {svc_NE_s3/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_hbm 1.875000000 $p; dict set ot_bound_names {svc_NE_s3/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {svc_NW_s4/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_hbm 1.954000000 $p; dict set ot_bound_names {svc_NW_s4/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {svc_NW_s5/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_hbm 1.890400000 $p; dict set ot_bound_names {svc_NW_s5/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {svc_NW_s6/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_hbm 1.890600000 $p; dict set ot_bound_names {svc_NW_s6/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {svc_NW_s7/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_hbm 1.875000000 $p; dict set ot_bound_names {svc_NW_s7/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {svc_NW_s0/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_hbm 1.996900000 $p; dict set ot_bound_names {svc_NW_s0/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {svc_NW_s1/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_hbm 1.875000000 $p; dict set ot_bound_names {svc_NW_s1/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {svc_NW_s2/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_hbm 1.988300000 $p; dict set ot_bound_names {svc_NW_s2/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {svc_NW_s3/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_hbm 1.975300000 $p; dict set ot_bound_names {svc_NW_s3/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {svc_SE_s4/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_hbm 1.894900000 $p; dict set ot_bound_names {svc_SE_s4/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {svc_SE_s5/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_hbm 1.873900000 $p; dict set ot_bound_names {svc_SE_s5/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {svc_SE_s6/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_hbm 2.140900000 $p; dict set ot_bound_names {svc_SE_s6/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {svc_SE_s7/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_hbm 2.071900000 $p; dict set ot_bound_names {svc_SE_s7/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {svc_SE_s8/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_hbm 1.994400000 $p; dict set ot_bound_names {svc_SE_s8/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {svc_SE_s0/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_hbm 1.890600000 $p; dict set ot_bound_names {svc_SE_s0/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {svc_SE_s1/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_hbm 2.008300000 $p; dict set ot_bound_names {svc_SE_s1/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {svc_SE_s2/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_hbm 2.189600000 $p; dict set ot_bound_names {svc_SE_s2/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {svc_SE_s3/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_hbm 1.875000000 $p; dict set ot_bound_names {svc_SE_s3/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {svc_SW_s4/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_hbm 1.954000000 $p; dict set ot_bound_names {svc_SW_s4/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {svc_SW_s5/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_hbm 1.890400000 $p; dict set ot_bound_names {svc_SW_s5/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {svc_SW_s6/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_hbm 1.890600000 $p; dict set ot_bound_names {svc_SW_s6/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {svc_SW_s7/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_hbm 1.875000000 $p; dict set ot_bound_names {svc_SW_s7/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {svc_SW_s0/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_hbm 1.996900000 $p; dict set ot_bound_names {svc_SW_s0/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {svc_SW_s1/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_hbm 1.875000000 $p; dict set ot_bound_names {svc_SW_s1/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {svc_SW_s2/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_hbm 1.988300000 $p; dict set ot_bound_names {svc_SW_s2/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {svc_SW_s3/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_hbm 1.975300000 $p; dict set ot_bound_names {svc_SW_s3/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w335_host/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_link 0.628900000 $p; dict set ot_bound_names {w335_host/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {lk_host/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_link 0.250400000 $p; dict set ot_bound_names {lk_host/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w310_lk_lk_N0/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_link 0.625400000 $p; dict set ot_bound_names {w310_lk_lk_N0/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w315_lk_lk_N1/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_link 0.625400000 $p; dict set ot_bound_names {w315_lk_lk_N1/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {lk_N0/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_link 0.250400000 $p; dict set ot_bound_names {lk_N0/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {lk_N1/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_link 0.250400000 $p; dict set ot_bound_names {lk_N1/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {lk_N2/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_link 0.250400000 $p; dict set ot_bound_names {lk_N2/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w319_lk_lk_N2/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_link 0.625400000 $p; dict set ot_bound_names {w319_lk_lk_N2/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {lk_N3/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_link 0.250400000 $p; dict set ot_bound_names {lk_N3/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w323_lk_lk_N3/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_link 0.625400000 $p; dict set ot_bound_names {w323_lk_lk_N3/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {lk_S0/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_link 0.251900000 $p; dict set ot_bound_names {lk_S0/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {lk_S1/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_link 0.251900000 $p; dict set ot_bound_names {lk_S1/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {lk_S2/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_link 0.251900000 $p; dict set ot_bound_names {lk_S2/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w289_lk_lk_S0/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_link 0.626900000 $p; dict set ot_bound_names {w289_lk_lk_S0/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w293_lk_lk_S1/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_link 0.626900000 $p; dict set ot_bound_names {w293_lk_lk_S1/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {lk_S3/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_link 0.251900000 $p; dict set ot_bound_names {lk_S3/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {lk_S4/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_link 0.251900000 $p; dict set ot_bound_names {lk_S4/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w298_lk_lk_S2/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_link 0.626900000 $p; dict set ot_bound_names {w298_lk_lk_S2/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w302_lk_lk_S3/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_link 0.626900000 $p; dict set ot_bound_names {w302_lk_lk_S3/ck[0]} 1; incr ot_clock_bound }
set p [ot_clock_pin {w306_lk_lk_S4/ck[0]}]
if {[llength $p]} { set_clock_latency -source -clock clk_link 0.626900000 $p; dict set ot_bound_names {w306_lk_lk_S4/ck[0]} 1; incr ot_clock_bound }
set_clock_uncertainty -setup 0.210 [all_clocks]
set_clock_uncertainty -hold 0.025 [all_clocks]
# 60 ps setup policy + unchanged conservative 150 ps die skew allowance.
puts "OT_CLOCK_CONTEXT corner=ss bound=$ot_clock_bound missing=[llength $ot_clock_missing]"
puts "OT_CLOCK_MISSING $ot_clock_missing"
set ot_unmapped_clock_pins {}
foreach net {n_clk_stream n_clk_serial n_clk_hbm n_clk_link} {
  foreach p [get_pins -quiet -of_objects [get_nets -quiet "$net $net\[0\]"]] {
    set n [get_full_name $p]
    if {![dict exists $ot_bound_names $n]} {lappend ot_unmapped_clock_pins $n}
  }
}
puts "OT_CLOCK_UNMAPPED count=[llength $ot_unmapped_clock_pins] pins=$ot_unmapped_clock_pins"

set ot_worst NA
foreach p [find_timing_paths -path_delay max -corner ss -group_path_count 1] {
  set s [get_property $p slack]
  if {$ot_worst eq "NA" || $s < $ot_worst} {set ot_worst $s}
}
puts "OT_CLOCK_CONTEXT_SLACK corner=ss path=max slack_ns=$ot_worst"
report_checks -path_delay max -corner ss -group_path_count 5 -format full_clock_expanded -digits 6 -fields {slew cap input_pins}
check_setup
puts OT_CLOCK_CONTEXT_DONE
