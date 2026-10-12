# ref_tile: exact abutment pins first (IO_CONSTRAINTS is otherwise sourced only at 3_2_place_iop, where it
# re-applies the same placement), then the spec's POST_TAPCELL hook (boundary flops FIRM at their pins)
source /src/physical/ref_tile_specs/smh/smh_pt_e_ref_p40_pins.tcl
source /src/physical/ref_tile_specs/smh/smh_pt_e_ref_p40_hops.tcl
