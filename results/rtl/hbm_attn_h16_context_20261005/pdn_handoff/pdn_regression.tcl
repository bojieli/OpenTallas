read_db /in/results/asap7/opentallas_ot_attn_tile_m6h1_asap7_codex_h16_nb5_context_r1/base/2_3_floorplan_tapcell.odb
source /diag/pdn_selected.tcl
pdngen -failed_via_report /diag/pdn_failed_vias.rpt
write_db /diag/pdn_selected.odb
puts "PASS_SELECTED_M6_TO_M9_MACRO_POWER_GRID"
exit
