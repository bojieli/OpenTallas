# Preserve separate compact register and macro CTS trees. The supported
# OpenROAD buffer-removal ECO removes only its added latency-balance chain.
# Actual ETM internal clocks and propagated-clock STA/SDC remain unchanged.
source /src/physical/s81_die_views/hbglue/parent_diamond.tcl
rename clock_tree_synthesis ot_head_native_clock_tree_synthesis
proc ot_head_remove_latency_chain {} {
 set names {}
 foreach i [[ord::get_db_block] getInsts] {
  if {[string match "delaybuf_*" [$i getName]]} {lappend names [$i getName]}
 }
 if {[llength $names]!=8} {error "expected exactly eight balance buffers, got $names"}
 set block [ord::get_db_block]
 foreach root {clkbuf_0_clk clkbuf_0_clk_regs} {
  if {[$block findInst $root]=="NULL"} {error "missing separate tree root $root"}
 }
 set nsink 0
 foreach inst [$block getInsts] {
  foreach pin [$inst getITerms] {
   if {[[$pin getMTerm] getName] ni {CLK clk}} {continue}
   if {[$pin getNet]=="NULL"} {error "disconnected clock before ECO [$inst getName]"}
   incr nsink
  }
 }
 if {$nsink!=1333} {error "unexpected original clock sinks $nsink"}
 puts "OT_HEAD_NATIVE_CLOCK_ECO remove_balance_buffers=$names"
 set original_names {}
 foreach i [$block getInsts] {lappend original_names [$i getName]}
 # Public API accepts instance-name varargs, not a pre-expanded collection.
 remove_buffers {*}$names
 set deleted {}
 foreach n $original_names {
  if {[$block findInst $n]=="NULL"} {lappend deleted $n}
 }
 if {[lsort $deleted] ne [lsort $names]} {error "clock ECO removed unexpected instances: $deleted"}
 foreach i [$block getInsts] {
  if {[lsearch -exact $original_names [$i getName]]<0} {error "clock ECO added unexpected instance [$i getName]"}
 }
 foreach root {clkbuf_0_clk clkbuf_0_clk_regs} {
  if {[$block findInst $root]=="NULL"} {error "clock ECO removed required separate root $root"}
 }
 set ndelay 0
 foreach i [[ord::get_db_block] getInsts] {
  if {[string match "delaybuf_*" [$i getName]]} {incr ndelay}
 }
 if {$ndelay!=0} {error "balance-chain physical ECO incomplete: $ndelay buffers"}
 set nsink_after 0
 foreach inst [$block getInsts] {
  foreach pin [$inst getITerms] {
   if {[[$pin getMTerm] getName] ni {CLK clk}} {continue}
   if {[$pin getNet]=="NULL"} {error "disconnected clock after ECO [$inst getName]"}
   incr nsink_after
  }
 }
 if {$nsink_after!=$nsink} {error "clock sink count changed during physical ECO"}
 puts "OT_HEAD_NATIVE_CLOCK_TOPOLOGY_VERIFIED actual_balance_buffers=$ndelay connected_sinks=$nsink_after"
 write_verilog /work/clock_topology_eco.v
}

proc clock_tree_synthesis {args} {
 puts "OT_HEAD_NATIVE_CLOCK_TOPOLOGY separate_trees_without_balance_chain"
 ot_head_native_clock_tree_synthesis {*}$args
 ot_head_remove_latency_chain
}
