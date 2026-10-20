set ::env(RESULTS_DIR) /case/routes/gate/work/orfs/results/asap7/opentallas_qkd_hr_cdc_pc_sram_asap7_ref_gate/base
read_db $::env(RESULTS_DIR)/3_4_place_resized.odb
source /audit/placement_contract.tcl
