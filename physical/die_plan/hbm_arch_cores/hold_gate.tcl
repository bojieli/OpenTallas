# HBM-CORES3 10-25 (COORD CORRECTION 00:46): post-CTS FF hold gate. STOP (structural -> plan/RTL fix, no repair)
# when FF hold WNS < -100 ps or > 2000 reg->reg hold endpoints on the CTS tree (SDC 25 ps hold uncertainty).
# HBM 10-25 01:40: the STOP counts reg->reg endpoints only (the clock-tree structure the gate is meant to catch);
# port paths (in->reg, reg->out) are reported, not gated here: they are repaired in the FF-only GRT step and gated
# >= 0 before DRT (run_kit_hbm.sh pre-route gate).
# HBM 10-25 restart: FF liberty, the IO vclk bound to the FF insertion (vclk_corner.tcl, OT_VCLK_FF: inputs AND outputs)
# and the kit RC basis (LAYER_PARASITICS_FILE = RCX-calibrated setRC_rcx.tcl; platform setRC only when absent).
if {![info exists ::env(PLIBS)] || ![llength $::env(PLIBS)]} { error "hold gate: BC_LIB_FILES missing" }
foreach l $::env(PLIBS) { if {$l ne ""} { read_liberty $l } }
read_db $::env(ODB)
read_sdc $::env(SDC)
set_propagated_clock [get_clocks clk]
if {[info exists ::env(OT_VCLK_FF)] && $::env(OT_VCLK_FF) ne ""} {
  source [file join [file dirname [file normalize [info script]]] vclk_corner.tcl]
  ot_vclk_bind ff
}
if {[info exists ::env(LAYER_PARASITICS_FILE)] && $::env(LAYER_PARASITICS_FILE) ne "" && [file exists $::env(LAYER_PARASITICS_FILE)]} {
  source $::env(LAYER_PARASITICS_FILE); set rcb $::env(LAYER_PARASITICS_FILE)
} else {
  source $::env(PLATFORM_DIR)/setRC.tcl; set rcb platform_setRC
}
estimate_parasitics -placement
array set n {rr 0 io 0}; array set wns {rr 0.0 io 0.0}
foreach p [find_timing_paths -path_delay min -group_path_count 20000 -endpoint_path_count 1 -slack_max 0] {
  set k rr
  if {[get_property [get_property $p startpoint] is_port] || [get_property [get_property $p endpoint] is_port]} { set k io }
  incr n($k)
  set s [get_property $p slack]
  if {$s < $wns($k)} { set wns($k) $s }
}
set verdict PASS
if {$wns(rr) < -100.0 || $n(rr) > 2000} { set verdict FAIL }
puts "OT_HOLD_GATE $verdict FF wns_ps [format %.2f $wns(rr)] endpoints $n(rr) reg2reg (limits wns -100 ps, 2000 endpoints); port paths (FF vclk) not gated here: [format %d $n(io)] endpoints wns [format %.2f $wns(io)]; rc $rcb"
