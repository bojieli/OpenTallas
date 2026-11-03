# Read only after the approved normal source-only SYNTH target has completed.
# An unplaced synth ODB supplies actual names/masters/nets, never macro/BPin poses.
read_db /work/run/results/asap7/dp_tt_ctlm/base/1_synth.odb
set ::env(OT_TT_SYNTH_ONLY) 1
set ::env(OT_TT_NATIVE_OUT) /work/producer/actual_synth.tsv
source /work/producer/export_inventory.tcl
exit
