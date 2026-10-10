# Opt-in recovery for the full-shape fused-head endpoint stacked ECO after
# DRT-0218 rejected its inherited guides. Install beside a pinned copy of the
# standard hold_eco scripts as hold_eco.tcl, with the original preserved as
# hold_eco_common.tcl. Start a new process: no second DRT in a failed session.
# RTL, clock, uncertainties, and boundary obligations are unchanged. Fresh
# routing is eligible only after the same TT/FF/DRC qualification passes.
set ::env(OT_GUIDES) 0
set ::env(OT_ALLOW_FRESH_GRT) 1
puts "OT_FH_FRESH_GUIDES explicit_opt_in 1 reason prior_DRT_0218_rejected_stacked_guides"
source /cl/hold_eco_common.tcl
