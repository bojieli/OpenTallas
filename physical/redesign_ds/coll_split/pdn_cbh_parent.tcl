# el1011-ds-coll 2026-10-11: PDN of the cb / ce PARENTS of hardened tiles.  Child abstracts (closed tiles routed with
# pdn_coll.tcl) expose VDD / VSS on M7 and obstruct M1-M7.  Parent: core grid with every layer stitched (M1 / M2 follow-
# pins for channel cells, M5 / M6 / M7 stripes cut around the children, M8 / M9 straps over everything; style of
# physical/hgi_idx_hier/pdn_hier.tcl, preamble 'PARENT PDN FOR HARD TILES'), children connected at their own pin layer
# M7 -> M8, both orientations used by the parents (R0, MY).
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M9}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M5} -width {0.12} -spacing {0.072} -pitch {5.4} -offset {0.300}
add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.096} -pitch {5.4} -offset {0.513}
add_pdn_stripe -grid {top} -layer {M7} -width {0.288} -spacing {0.096} -pitch {10.8} -offset {1.0}
add_pdn_stripe -grid {top} -layer {M8} -width {0.474} -spacing {2.226} -pitch {5.4} -offset {1.5}
add_pdn_stripe -grid {top} -layer {M9} -width {0.474} -spacing {2.226} -pitch {5.4} -offset {1.5}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M6}
add_pdn_connect -grid {top} -layers {M6 M7}
add_pdn_connect -grid {top} -layers {M7 M8}
add_pdn_connect -grid {top} -layers {M8 M9}
define_pdn_grid -macro -cells {dsfd_coll_cbr dsfd_coll_cbf dsfd_coll_cbfj dsfd_coll_cbq0 dsfd_coll_cbq dsfd_coll_ces0 dsfd_coll_cesn dsfd_coll_cef dsfd_coll_cele dsfd_coll_celp dsfd_coll_ceq} \
    -orient {R0 MY MX R180} -halo {0.5 0.5 0.5 0.5} -voltage_domains {CORE} -name {children}
add_pdn_connect -grid {children} -layers {M7 M8}
