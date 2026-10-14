read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /work/fixed.lef
set found {}
foreach lib [[ord::get_db] getLibs] { foreach master [$lib getMasters] { lappend found [$master getName] } }
foreach name {dsfd_rly_15_EN dsfd_rly_15_SN dsfd_rly_2_ES dsfd_rly_2_EW dsfd_rly_2_NE dsfd_rly_2_NS dsfd_rly_2_NW dsfd_rly_2_SN dsfd_rly_2_WE dsfd_rly_2_WS dsfd_rly_54_EW dsfd_rly_63_ES dsfd_rly_63_NE dsfd_rly_63_NS dsfd_rly_63_SE dsfd_rly_63_WE dsfd_rly_63_WN dsfd_rly_63_WS dsfd_rly_66_NS dsfd_rly_66_SN dsfd_rly_68_EW} { if {[lsearch -exact $found $name] < 0} { error "missing bound master $name" } }
puts "BOUND_LEF_PARSE_PASS masters=21"
