# GENERATED-COPY of tools/die_plan/grt_pre.tcl (PRE_GLOBAL_ROUTE hook, FLOW 2026-10-25): FF-only GRT step binds the IO
# virtual clock to the FF insertion (vclk_corner.tcl, OT_VCLK_CORNER=ff from run_kit.sh) before the hold repair;
# optional repeater pitch (grt_maxwire.tcl, OT_MAXWIRE_UM).
set gp_dir [file dirname [file normalize [info script]]]
source [file join $gp_dir vclk_corner.tcl]
if {[info exists ::env(OT_MAXWIRE_UM)] && $::env(OT_MAXWIRE_UM) ne ""} { source [file join $gp_dir grt_maxwire.tcl] }
