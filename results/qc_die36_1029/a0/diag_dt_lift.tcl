# DIE-QC-36 A0 DIAGNOSTIC ONLY (diag copies, never a closure candidate): find what TritonCTS connects to the planned
# dont_touch tree nets (ODB-0373 on mp_a0_t7_out). Lifts dont_touch on the planned non-open tree nets for the TritonCTS
# call only, then lists every iterm that appeared on / left those nets, and restores dont_touch.
if {![llength [info commands ::ot_diag_inner_cts]]} {
  rename ::clock_tree_synthesis ::ot_diag_inner_cts
  proc ::clock_tree_synthesis {args} {
    set before [dict create]
    dict for {node net} $::ot_ci_tree_out {
      if {[lsearch -exact $::ot_ci_tree_open $net] >= 0 || ![$net isDoNotTouch]} continue
      set its {}; foreach it [$net getITerms] {lappend its "[[$it getInst] getName]/[[$it getMTerm] getName]"}
      dict set before $net [lsort $its]; $net setDoNotTouch 0
    }
    try {::ot_diag_inner_cts {*}$args} finally {
      dict for {net its} $before {
        set now {}; foreach it [$net getITerms] {lappend now "[[$it getInst] getName]/[[$it getMTerm] getName]"}
        set now [lsort $now]
        set add [lmap x $now {expr {[lsearch -exact $its $x] < 0 ? $x : [continue]}}]
        set gone [lmap x $its {expr {[lsearch -exact $now $x] < 0 ? $x : [continue]}}]
        if {[llength $add] || [llength $gone]} {
          puts "OT_DIAG_PLANNED_NET [$net getName] added=[llength $add] [lrange $add 0 9] removed=[llength $gone] [lrange $gone 0 9]"
        }
        $net setDoNotTouch 1
      }
    }
  }
}
