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
source /work/vclk_measured_hold.tcl
puts "K33_MEAS FF [ot_vmh_pinreg_mean]"
puts "K33_REF [ot_vmh_reference]"
