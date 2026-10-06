set actual_parent_file /src/physical/hbm_die_abstracts_20261006/links/callers/actual_parent_column_W564.tcl
set expected_source_sha256 004b4c7fd2c85424b829c591e70f6fcadd2124c75c7ba6aa6f8dbe3634e8777a
source /src/physical/hbm_die_abstracts_20261006/links/callers/parent_contract.tcl
# Exact dsfd_cfifo parent roots from S81 r8. No borrowed child clock or cuts.
create_clock -name writer -period 833.333333 [get_ports xf*]
create_clock -name column -period 833.333333 [get_ports ck*]
create_generated_clock -name column_out -source [get_ports ck*] -master_clock column -divide_by 1 [get_ports co*]
create_generated_clock -name return_root -source [get_ports ck*] -master_clock column -divide_by 1 [get_ports rf*]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
# Actual primitive guard0/D4/OFFSET2 bound; no false paths/clock groups.
set_max_delay -ignore_clock_latency 356.666667 -from [get_clocks writer] -to [get_clocks column]
set_max_delay -ignore_clock_latency 356.666667 -from [get_clocks column] -to [get_clocks writer]
set_min_delay -ignore_clock_latency 0 -from [get_clocks writer] -to [get_clocks column]
set_min_delay -ignore_clock_latency 0 -from [get_clocks column] -to [get_clocks writer]
owner_input writer [get_ports xd*]
owner_input column [get_ports {ri* st* rst*}]
owner_output column_out [get_ports {xa* xb* cc* rs*}]
owner_output return_root [get_ports rd*]
foreach pattern {co* rf*} {
 set port [get_ports $pattern]
 if {[llength $port]!=1} {error "ambiguous actual clock output $pattern"}
 set root [get_full_name $port]
 if {![dict exists $parent_contract receiver_load_ui $root]} {error "missing actual column/return root load $root"}
 set_load [dict get $parent_contract receiver_load_ui $root] $port
}
set_max_fanout 32 [current_design]
