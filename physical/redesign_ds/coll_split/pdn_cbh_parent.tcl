# el1011-ds-coll 2026-10-11: PDN of the cb PARENT (dsfd_coll_cbh).  The children (closed hardened tiles) own M1-M7 and
# expose VDD / VSS pins on M7 (pdn_coll.tcl); the parent owns M8 / M9 straps over everything and connects them down onto
# the children's M7 pins; channel cells get M1 / M2 follow-pins stitched up to M8.
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M9}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M8} -width {0.474} -spacing {2.226} -pitch {5.4} -offset {1.5}
add_pdn_stripe -grid {top} -layer {M9} -width {0.474} -spacing {2.226} -pitch {5.4} -offset {1.5}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M8}
add_pdn_connect -grid {top} -layers {M8 M9}
define_pdn_grid -macro -cells {dsfd_coll_cbr dsfd_coll_cbf dsfd_coll_cbfj dsfd_coll_cbq0 dsfd_coll_cbq} -halo {0.5 0.5 0.5 0.5} \
    -voltage_domains {CORE} -name {children}
add_pdn_connect -grid {children} -layers {M7 M8}
