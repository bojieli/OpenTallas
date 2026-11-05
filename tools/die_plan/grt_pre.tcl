# GENERATED-COPY of tools/die_plan/grt_pre.tcl (PRE_GLOBAL_ROUTE hook, FLOW 2026-10-25): FF-only GRT step binds the IO
# virtual clock to the FF insertion (vclk_corner.tcl, OT_VCLK_CORNER=ff from run_kit.sh) before the hold repair;
# optional repeater pitch (grt_maxwire.tcl, OT_MAXWIRE_UM).
set gp_dir [file dirname [file normalize [info script]]]
# KW-FIX-16 11-05: a GRT resumed from 4_cts.odb takes the signal layer range from MIN/MAX_ROUTING_LAYER (grt_layers.tcl)
if {[file exists [file join $gp_dir grt_layers.tcl]]} { source [file join $gp_dir grt_layers.tcl] }
source [file join $gp_dir vclk_corner.tcl]
if {[info exists ::env(OT_MAXWIRE_UM)] && $::env(OT_MAXWIRE_UM) ne ""} { source [file join $gp_dir grt_maxwire.tcl] }
# FLOW-23 11-02 HOLD-GUARD-GRT: progress/time bound for the single-mode GRT hold repair (hold_guard_grt.tcl; OT_HOLD_GUARD=0 off)
if {[file exists [file join $gp_dir hold_guard_grt.tcl]]} { source [file join $gp_dir hold_guard_grt.tcl] }
