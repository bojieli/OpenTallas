# [cg] 2026-10-10 post-SDC (corner STA / hold ECO): nbr_clk_i at this session's measured input pin-flop insertion
# (physical/common_flow/nbr_in_ref.tcl).  Ideal clocks: no change.
if {[file exists /src/physical/common_flow/nbr_in_ref.tcl]} {
  if {[catch {source /src/physical/common_flow/nbr_in_ref.tcl; ot_nir_apply post} e]} { puts "OT_NIR post: ERROR $e" }
}
