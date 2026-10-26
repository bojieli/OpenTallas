# Plan-defined, BEFORE any build. Not a post-CTS timing ECO.
create_ndr -name head_core_clock_4w -width {M4 0.128 M5 0.128} -spacing {M4 0.128 M5 0.128}
set b [ord::get_db_block]
set nd [$b findNonDefaultRule head_core_clock_4w]
foreach n [$b getNets] { if {[$n getSigType] eq "CLOCK"} { $n setNonDefaultRule $nd } }
set_routing_layers -signal M2-M5 -clock M4-M5
# Per-type generator must materialize the model's fixed-depth sink sets first.
