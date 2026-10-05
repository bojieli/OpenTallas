read_db /in/results/asap7/opentallas_ot_attn_tile_m6h1_asap7_codex_h16_nb5_context_r1/base/2_2_floorplan_macro.odb
tapcell -distance 25 -tapcell_master TAPCELL_ASAP7_75t_R -endcap_master TAPCELL_ASAP7_75t_R -halo_width_x 5 -halo_width_y 5
source /diag/pdn_selected.tcl
pdngen -failed_via_report /diag/pdn_selected_halo5_failed_vias.rpt
write_db /diag/pdn_selected_halo5.odb
puts "PASS_SELECTED_M6_TO_M9_POWER_AND_5UM_ROW_HALO"
exit
