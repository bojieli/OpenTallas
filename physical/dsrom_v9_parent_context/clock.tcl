set_thread_count 4
set block [ord::get_db_block]
# Native source clock metal. Clock NDR gives an actual spacing guard; not a shield credit.
set_wire_rc -clock -layer M8
set_routing_layers -signal M2-M7 -clock M7-M8
set rule [$block findNonDefaultRule context_clock_guard]
if {$rule eq "NULL"} {
 create_ndr -name context_clock_guard -spacing {M8 0.144} -width {M8 0.096}
 set rule [$block findNonDefaultRule context_clock_guard]
}
if {$rule eq "NULL"} {error "clock NDR absent"}
foreach net [$block getNets] {if {[$net getSigType] eq "CLOCK" || [$net getName] eq "clk"} {$net setNonDefaultRule $rule}}
source /src/physical/dsrom_v9_parent_context/replay_checks.tcl
