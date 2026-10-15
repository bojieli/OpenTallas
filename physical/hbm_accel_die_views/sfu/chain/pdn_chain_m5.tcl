# el1011-hbm-sfu 10-11: PDN of the SFU sigmoid-chain sub-tile (ot_hdc_v41x_sfu_chain), a hard child INSIDE the SFU
# lane.  Preamble PARENT PDN UPDATE 3 option B: the child's signals stop at M5 (route_lane MAXL M5) and its power
# pins are its M5 stripes; the lane's own M6 straps (pdn_lane_m6_e27.tcl, pitch 5.4) run over the child and via down
# onto these M5 pins, so the lane keeps its M6 contract to the tile (no M7 inside the lane).  First M5 strap at 2.70
# um, clear of the W-face M4 signal pins (193869878: VSS via pads under the pins at x 0.25-0.35).
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M5}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M5} -width {0.12} -spacing {0.072} -pitch {5.4} -offset {2.700}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
