# H-SM 2200 q1_core kits: block macro-to-macro gaps < 20 um (abutted SRAM stack .024 um slivers; 20.136 um channels stay
# placeable), then the floorplan margin lint dump and the post-IO ODB the pre-route gate lints.
set ot_sliver_um 20.0
source /src/physical/common_flow/macro_channel_block.tcl
source /src/tools/fp_margin_lint.tcl
ot_fp_lint_dump [file join $::env(RESULTS_DIR) identity_actual_pin_pg.json]
orfs_write_db $::env(RESULTS_DIR)/3_2_place_iop.odb
