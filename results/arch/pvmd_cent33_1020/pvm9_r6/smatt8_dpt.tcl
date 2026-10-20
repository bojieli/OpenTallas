set R /work/results/asap7/opentallas_ot_hbm_sm_pv_merge_distributed_asap7_ref_gate/base
set ::env(RESULTS_DIR) $R
read_db $R/3_4_place_resized.odb
source /work/hooks/pre_detail_place_out_flop_release.tcl
set_placement_padding -global -left 0 -right 0
if {$::env(V) eq "diamond" || $::env(V) eq "diamond_nodpo"} { detailed_placement -use_diamond_legalizer } else { detailed_placement }
puts "AFTER_DPL [check_placement -verbose]"
if {$::env(V) eq "diamond" || $::env(V) eq "neg"} { catch {improve_placement -max_displacement "5 1"} e; puts "DPO $e" }
optimize_mirroring
puts "FINAL_VIOL [check_placement -verbose]"
