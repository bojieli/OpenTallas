source /src/physical/hbm_hc/HC_residual_half_exact_source_pins.tcl
# ORFS sources hooks inside a procedure; publish data explicitly to audit namespace.
set ::hbm_geometry_requested_outline $hbm_geometry_requested_outline
set ::hbm_geometry_pin_requests $hbm_geometry_pin_requests
source /src/physical/hbm_hc/assigned_pin_audit.tcl
hbm_assigned_pins::place
