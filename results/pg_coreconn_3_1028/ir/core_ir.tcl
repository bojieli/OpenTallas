# PG-CORECONN-3: in-core IR of a routed core view (own PDN M1/M2 rails + M2->M5 + M5 straps = core PG pins).
# Sources = M5 straps (PSM -source_type STRAPS; the tile lands a via on every M5/M6 crossing). STA power at regs+inputs OT_ACT.
# PG-CORECONN-2 core_ir.tcl method, parameterised.
foreach f [lsort [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_TT_nldm_*.lib*]] { read_liberty $f }
foreach f [glob -nocomplain /c/macros/*_tt.lib] { read_liberty $f }
set B $::env(OT_BASE); set tag $::env(OT_TAG); set a $::env(OT_ACT)
read_db $B/6_final.odb
read_sdc $B/6_final.sdc
read_spef $B/6_final.spef
set_propagated_clock [all_clocks]
foreach r [all_registers] { foreach p [get_pins -quiet -of_objects $r -filter "direction == output"] { set_power_activity -pins $p -activity $a -duty 0.5 } }
foreach p [all_inputs -no_clocks] { set_power_activity -input_ports $p -activity $a -duty 0.5 }
report_power -digits 6 > /o/power_core_$tag.rpt
set bb [[ord::get_db_block] getDieArea]; set dbu [[ord::get_db_block] getDbUnitsPerMicron]
puts "OT_CORE_AREA_MM2 [expr {double([$bb dx])*[$bb dy]/$dbu/$dbu*1e-6}]"
set_pdnsim_net_voltage -net VDD -voltage 0.70
set_pdnsim_net_voltage -net VSS -voltage 0.0
foreach net {VDD VSS} {
  puts "OT_IR_BEGIN $tag $net"
  analyze_power_grid -net $net -source_type STRAPS -error_file /o/err_core_${tag}_$net.rpt -voltage_file /o/volt_core_${tag}_$net.rpt
  puts "OT_IR_END $tag $net"
}
