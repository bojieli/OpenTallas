# DIE-S81-26: floorplan + master_slice (core tree cells) + face flops, enable isolation OFF -> write ODB for the enable packer site map
read_db /cen/run/results/asap7/kl_ot_v41_bf_col_ds81_25_$::env(V)/base/2_floorplan.odb
set ::env(OT_BFI_TSV) /nonexistent
source /work/face_flops.tcl
write_db /work/pass1.odb
puts PASS1_DONE
exit
