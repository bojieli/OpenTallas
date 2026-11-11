export LAYER_PARASITICS_FILE=/work/setRC_rcx.tcl
for o in /work/run/results/asap7/dp_serdes__t14/base/4_cts.odb /p/rep/relay_plain_repaired.odb; do echo "== $o"; ODBX=$o /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit /p/rep/tt_after.tcl 2>&1 | grep TTX; done
