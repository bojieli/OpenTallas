# DOMS coll_blk stream ucie
# INSERTION_COMPENSATED tt
# OWNER_CLOCK_BUDGET v1
set_cmd_units -time ps
set ot_clock_bound 0
set ot_pins {}
set p [get_pins -quiet {c0/ck}]
if {[llength $p] != 1} { error "clock boundary pin missing or ambiguous: c0/ck" }
lappend ot_pins [lindex $p 0]
create_clock -name coll_blk -period 5000.000000 $ot_pins
set_clock_latency -source -clock [get_clocks coll_blk] -100.000000 [get_pins {c0/ck}]
incr ot_clock_bound
# BUDGET coll_blk -> coll_blk: setup 60 + skew 90 ps; hold H1 100 ps
set_clock_uncertainty -setup 150.000000 -from [get_clocks coll_blk] -to [get_clocks coll_blk]
set_clock_uncertainty -hold 100.000000 -from [get_clocks coll_blk] -to [get_clocks coll_blk]
set ot_pins {}
set p [get_pins -quiet {a0/ck}]
if {[llength $p] != 1} { error "clock boundary pin missing or ambiguous: a0/ck" }
lappend ot_pins [lindex $p 0]
create_clock -name stream -period 833.333333 $ot_pins
set_clock_latency -source -clock [get_clocks stream] -100.000000 [get_pins {a0/ck}]
incr ot_clock_bound
# BUDGET stream -> stream: setup 60 + skew 90 ps; hold H1 100 ps
set_clock_uncertainty -setup 150.000000 -from [get_clocks stream] -to [get_clocks stream]
set_clock_uncertainty -hold 100.000000 -from [get_clocks stream] -to [get_clocks stream]
set ot_pins {}
set p [get_pins -quiet {b0/ck}]
if {[llength $p] != 1} { error "clock boundary pin missing or ambiguous: b0/ck" }
lappend ot_pins [lindex $p 0]
create_clock -name ucie -period 1000.000000 $ot_pins
set_clock_latency -source -clock [get_clocks ucie] -100.000000 [get_pins {b0/ck}]
incr ot_clock_bound
# BUDGET ucie -> ucie: setup 60 + skew 90 ps; hold H1 100 ps
set_clock_uncertainty -setup 150.000000 -from [get_clocks ucie] -to [get_clocks ucie]
set_clock_uncertainty -hold 100.000000 -from [get_clocks ucie] -to [get_clocks ucie]
set_clock_uncertainty -setup 150.000000 -from [get_clocks coll_blk] -to [get_clocks stream]
set_clock_uncertainty -hold 100.000000 -from [get_clocks coll_blk] -to [get_clocks stream]
set_clock_uncertainty -setup 150.000000 -from [get_clocks coll_blk] -to [get_clocks ucie]
set_clock_uncertainty -hold 100.000000 -from [get_clocks coll_blk] -to [get_clocks ucie]
set_clock_uncertainty -setup 150.000000 -from [get_clocks stream] -to [get_clocks coll_blk]
set_clock_uncertainty -hold 100.000000 -from [get_clocks stream] -to [get_clocks coll_blk]
set_clock_uncertainty -setup 150.000000 -from [get_clocks stream] -to [get_clocks ucie]
set_clock_uncertainty -hold 100.000000 -from [get_clocks stream] -to [get_clocks ucie]
set_clock_uncertainty -setup 150.000000 -from [get_clocks ucie] -to [get_clocks coll_blk]
set_clock_uncertainty -hold 100.000000 -from [get_clocks ucie] -to [get_clocks coll_blk]
set_clock_uncertainty -setup 150.000000 -from [get_clocks ucie] -to [get_clocks stream]
set_clock_uncertainty -hold 100.000000 -from [get_clocks ucie] -to [get_clocks stream]
set_propagated_clock [all_clocks]
puts "OT_COMPENSATED_CLOCK corner=tt bound=$ot_clock_bound"
