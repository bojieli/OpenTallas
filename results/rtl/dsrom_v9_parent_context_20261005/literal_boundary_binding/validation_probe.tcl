set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [list asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib] {read_liberty $L/$f}
read_db /input/1_synth.odb
set_units -time ps -capacitance fF
read_sdc /input/1_synth.sdc
source /src/physical/dsrom_v9_parent_context/replay_checks.tcl
source /out/literal_boundary_pins.tcl
puts OT_PARENT_LITERAL_BOUNDARY_PINS_PASS
