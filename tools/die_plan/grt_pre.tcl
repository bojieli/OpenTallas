# GENERATED-COPY of tools/die_plan/grt_pre.tcl (PRE_GLOBAL_ROUTE hook, FLOW 2026-10-25): FF-only GRT step binds the IO
# virtual clock to the FF insertion (vclk_corner.tcl, OT_VCLK_CORNER=ff from run_kit.sh) before the hold repair;
# optional repeater pitch (grt_maxwire.tcl, OT_MAXWIRE_UM).
set gp_dir [file dirname [file normalize [info script]]]
source [file join $gp_dir vclk_corner.tcl]
if {[info exists ::env(OT_MAXWIRE_UM)] && $::env(OT_MAXWIRE_UM) ne ""} { source [file join $gp_dir grt_maxwire.tcl] }
# OT_CLK_ROUTING_LAYERS (opt-in, CLOCK-RESET 10-25, e.g. M4-M5): this ORFS never reads MIN_CLK_ROUTING_LAYER at GRT
# (floorplan.tcl sets -signal only; platform fastroute.tcl is not sourced), so clock nets fall to M2/M3 (E5: trunk
# slew 606 ps). Hardened-block clock nets route on the top two block layers, set explicitly here.
if {[info exists ::env(OT_CLK_ROUTING_LAYERS)] && $::env(OT_CLK_ROUTING_LAYERS) ne ""} {
  set_routing_layers -signal $::env(MIN_ROUTING_LAYER)-$::env(MAX_ROUTING_LAYER) -clock $::env(OT_CLK_ROUTING_LAYERS)
  puts "OT_CLK_ROUTING_LAYERS: clock nets on $::env(OT_CLK_ROUTING_LAYERS), signal $::env(MIN_ROUTING_LAYER)-$::env(MAX_ROUTING_LAYER)"
}
