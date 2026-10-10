# bf-arch: abstract LEF + TT/FF timing models of a routed hardened BF block. env: ODB SDC SPEF CORNER POST OUT NAME MACRO(optional)
set L /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $L/lef/asap7_tech_1x_201209.lef
read_lef $L/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef $L/lef/asap7sc7p5t_28_L_1x_220121a.lef
if {$::env(MACRO) ne ""} { read_lef $::env(MACRO).lef }
set C [string toupper $::env(CORNER)]
foreach vt {RVT LVT} { foreach f [glob $L/lib/NLDM/asap7sc7p5t_*_${vt}_${C}_nldm_*] { read_liberty $f } }
if {$::env(MACRO) ne ""} { read_liberty $::env(MACRO)_[string tolower $C].lib }
read_db $::env(ODB)
read_sdc $::env(SDC)
read_spef $::env(SPEF)
set_propagated_clock [all_clocks]
if {$::env(POST) ne ""} { read_sdc $::env(POST) }
if {$C eq "TT"} { write_abstract_lef -bloat_occupied_layers $::env(OUT)/$::env(NAME).lef }
write_timing_model -library_name $::env(NAME)_[string tolower $C] $::env(OUT)/$::env(NAME)_[string tolower $C].lib
puts "OT_EXPORT done $C"
exit
