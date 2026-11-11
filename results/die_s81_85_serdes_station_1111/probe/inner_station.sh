PL=/OpenROAD-flow-scripts/flow/platforms/asap7
export PLIBS="$(ls $PL/lib/NLDM/*RVT_FF_nldm*.lib* | tr "\n" " ") $(ls /work/macros/*_ff.lib | tr "\n" " ")"
B=$(ls -d /work/run/results/asap7/*/base)
export ODB=$B/4_cts.odb SDC=$B/4_cts.sdc PLATFORM_DIR=$PL
for v in OT_VCLK_FF OT_HOLD_IN_MIN OT_HOLD_OUT_MIN OT_TAP_WINDOW; do export $v=$(sed -n "s/^export $v = //p" /work/config.mk); done
export LAYER_PARASITICS_FILE=/work/setRC_rcx.tcl
exec /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit /p/rep/relrep_station.tcl
