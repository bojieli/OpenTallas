# A second independent regional clock tree for the PHY domain. The streaming
# tree is built by clock_split_km.tcl; use distinct instance/net/global names.
set ::env(OT_HCKKM_K) 8
set ::env(OT_HCKKM_PORT) ckh
set ot_hckkm_fd [open /src/physical/common_flow/clock_split_km.tcl r]
set ot_hckkm_body [read $ot_hckkm_fd]
close $ot_hckkm_fd
eval [string map {ot_ckkm ot_hckkm OT_CKKM OT_HCKKM CLOCK_SPLIT_KM HCLK_SPLIT_KM} $ot_hckkm_body]
