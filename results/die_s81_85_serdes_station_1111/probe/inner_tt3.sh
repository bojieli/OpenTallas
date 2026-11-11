export LAYER_PARASITICS_FILE=/work/setRC_rcx.tcl
ODBX=/p/rep/relay_station_repaired.odb /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit /p/rep/tt_after.tcl 2>&1 | grep TTX
