# Prototype: native whole-parent CTS, exact signed ETM macro insertion.
# Protected faces retain logic/data/placement; release only during clock-tree rewrite.
rename clock_tree_synthesis ot_nl_native_clock_tree_synthesis
proc clock_tree_synthesis {args} {
 set b [ord::get_db_block];set protected {}
 foreach i [$b getInsts] {
  if {[$i isDoNotTouch]} {
   foreach it [$i getITerms] {
    if {[[$it getMTerm] getName] eq "CLK"} {lappend protected $i;$i setDoNotTouch 0;break}
   }
  }
 }
 puts "NL_NATIVE_CTS temporarily release [llength $protected] original protected clock sinks"
 set rc [catch {ot_nl_native_clock_tree_synthesis {*}$args} msg opts]
 foreach i $protected {$i setDoNotTouch 1}
 if {$rc} {return -options $opts $msg}
 puts "NL_NATIVE_CTS restored [llength $protected] original sink protections"
}
