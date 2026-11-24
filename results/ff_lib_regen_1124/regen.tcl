# CORE-TAP-BUDGET 11-24: regenerate a signed core's ETM (TT and FF) from its signed routed DB.  Report-only.
# env: OT_C = TT|FF, OT_MOD = module name.  Mounts: /r = view regen dir (base/6_final.odb, base/6_final.spef,
# macros/*_{tt,ff}.lib, clocks.txt) ; output /r/out_<c>.lib
set c $::env(OT_C); set lc [string tolower $c]
set N /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [list $N/asap7sc7p5t_AO_RVT_${c}_nldm_211120.lib.gz $N/asap7sc7p5t_INVBUF_RVT_${c}_nldm_220122.lib.gz \
              $N/asap7sc7p5t_OA_RVT_${c}_nldm_211120.lib.gz $N/asap7sc7p5t_SEQ_RVT_${c}_nldm_220123.lib \
              $N/asap7sc7p5t_SIMPLE_RVT_${c}_nldm_211120.lib.gz] { read_liberty $f }
foreach f [lsort [glob -nocomplain /r/macros/*_${lc}.lib]] { puts "OT_REGEN macro $f"; read_liberty $f }
read_db /r/base/6_final.odb
if {[file exists /r/base/6_final.spef]} { read_spef /r/base/6_final.spef; puts "OT_REGEN parasitics spef" } else {
  source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
  extract_parasitics -ext_model_file /OpenROAD-flow-scripts/flow/platforms/asap7/rcx_patterns.rules
  write_spef /r/rcx_$lc.spef; read_spef /r/rcx_$lc.spef; puts "OT_REGEN parasitics rcx" }
set fp [open /r/clocks.txt]; set cks [split [string trim [read $fp]] \n]; close $fp
set cks [lsearch -all -inline -not -regexp $cks {^(VDD|VSS)$}]
foreach p $cks { create_clock -name ck_[regsub -all {[^A-Za-z0-9_]} $p _] -period 833.0 [get_ports $p] }
set_propagated_clock [all_clocks]
puts "OT_REGEN $::env(OT_MOD) corner $c clocks $cks"
write_timing_model -library_name $::env(OT_MOD) -cell_name $::env(OT_MOD) /r/out_${lc}.lib
puts "OT_REGEN WROTE /r/out_${lc}.lib"
