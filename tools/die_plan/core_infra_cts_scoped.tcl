# Scoped plan tree: normal CTS remains enabled for the explicitly ordinary
# input roots; the selected root is built only below its planned open leaves.
if {![info exists ::ot_ci_scope_owned] || ![llength [info commands ot_ci_scope_disjoint]]} {
  error "OT_CORE_SCOPE_NO_GUARD scoped CTS needs the root guard before any kit clock editor"
}
proc ot_ci_scope_check_clock_sources {} {
  set blk [ord::get_db_block]; set found {}
  foreach clock [all_clocks] {
    foreach source [get_property $clock sources] {
      set name [get_full_name $source]; set bt [$blk findBTerm $name]
      if {$bt eq "NULL" || [$bt getIoType] ne "INPUT"} continue
      if {[lsearch -exact $::ot_ci_scope_roots $name] < 0} {
        error "OT_CORE_SCOPE_UNDECLARED_ROOT actual input clock source $name is absent from root_scope"
      }
      dict set found $name 1
    }
  }
  foreach root [concat [list $::ot_ci_scope_owned] $::ot_ci_scope_cts_roots] {
    if {![dict exists $found $root]} {error "OT_CORE_SCOPE_ROOT_NOT_CLOCKED required input root $root has no STA clock"}
  }
}
if {[llength [info commands ot_ci_leaf_rebind]] == 0} {
  # Rebinding has a separate selected-root proof path. Keep this initial scoped
  # implementation explicit rather than silently omitting a requested rebind.
  if {[info exists ::ot_ci_leaf_rebind_leaves]} {error "OT_CORE_SCOPE_REBIND scoped tree does not support post_place_rebind"}
}
if {![llength [info commands ::ot_ci_tritoncts]]} {
  rename ::clock_tree_synthesis ::ot_ci_tritoncts
  proc ::clock_tree_synthesis {args} {
    ot_ci_scope_check_clock_sources
    set cones [ot_ci_scope_disjoint]
    set selected [dict get $cones $::ot_ci_scope_owned nets]
    set blk [ord::get_db_block]; set open {}; set ordinary {}; set cts_ordinary {}; set normal {}; set protected [list $::ot_ci_scope_owned]
    foreach nm $selected {
      set n [$blk findNet $nm]
      if {[$n getSigType] ne "CLOCK" || [$n isDoNotTouch]} continue
      set drv [$n getFirstOutput]
      if {$drv eq "NULL" || $drv eq "" || ![[$drv getInst] isDoNotTouch]} continue
      lappend open $nm
    }
    if {[llength $open] != $::ot_ci_cts_plan_open} {
      error "OT_CORE_INFRA_CTS_OPEN_COUNT [llength $open] selected-root open nets != plan $::ot_ci_cts_plan_open"
    }
    foreach root $::ot_ci_scope_roots {
      if {$root eq $::ot_ci_scope_owned} continue
      set ordinary [concat $ordinary [dict get $cones $root nets]]
      if {[lsearch -exact $::ot_ci_scope_cts_roots $root] >= 0} {
        lappend normal [[[$blk findBTerm $root] getNet] getName]
        set cts_ordinary [concat $cts_ordinary [dict get $cones $root nets]]
      } else {lappend protected $root}
    }
    set nck 0; set pinroots {}; set netroots {}
    dict for {root info} $cones {foreach net [dict get $info nets] {dict set netroots $net $root}}
    foreach p [all_registers -clock_pins] {
      set it [sta::sta_to_db_pin $p]
      if {$it eq "NULL" || $it eq ""} continue
      set n [$it getNet]
      if {$n eq "NULL"} {error "OT_CORE_SCOPE_UNCLOCKED_PIN $p"}
      set nm [$n getName]; incr nck
      if {[dict exists $netroots $nm]} {dict set pinroots $it [dict get $netroots $nm]}
      if {[lsearch -exact $selected $nm] >= 0} {
        if {!([$n isDoNotTouch] || [lsearch -exact $open $nm] >= 0)} {
          error "OT_CORE_INFRA_CTS_UNPLANNED_CLOCK_PINS selected root: [[$it getInst] getName]/[[$it getMTerm] getName]"
        }
      } elseif {[lsearch -exact $ordinary $nm] < 0} {
        error "OT_CORE_SCOPE_UNDECLARED_CLOCK_PIN [[$it getInst] getName]/[[$it getMTerm] getName] on $nm"
      }
    }
    # Preserve explicit caller CTS targets on ordinary roots; do not turn a
    # generator's leaf-only CTS method back into a full-root rebuild.
    set a {}; set requested {}; set skip 0
    foreach x $args {
      if {$skip} {set requested $x; set skip 0; continue}
      if {$x eq "-clk_nets"} {set skip 1; continue}
      lappend a $x
    }
    if {$skip} {error "OT_CORE_SCOPE_CTS_ARGS -clk_nets requires a value"}
    if {[llength $requested]} {
      set normal {}
      foreach nm $requested {
        if {[lsearch -exact $cts_ordinary $nm] >= 0} {lappend normal $nm} elseif {[lsearch -exact $selected $nm] < 0} {
          error "OT_CORE_SCOPE_CTS_TARGET undeclared clock net $nm"
        }
      }
    }
    set targets [lsort -unique [concat $open $normal]]
    set before [ot_ci_scope_snapshot $protected $open]
    if {![llength $targets]} {puts "OT_CORE_SCOPE_CTS no buildable nets; checked $nck clock pins"; return}
    puts "OT_CORE_SCOPE_CTS $::ot_ci_scope_owned: [llength $open] planned open nets + [llength $normal] ordinary CTS nets; $nck pins"
    try {
      set result [::ot_ci_tritoncts {*}$a -clk_nets $targets]
    } finally {
      if {[ot_ci_scope_snapshot $protected $open] ne $before} {
        error "OT_CORE_SCOPE_CTS_CHANGED TritonCTS changed the selected planned tree outside its open leaves"
      }
      set after [ot_ci_scope_disjoint]; set netroots {}
      dict for {root info} $after {foreach net [dict get $info nets] {dict set netroots $net $root}}
      dict for {pin root} $pinroots {
        set n [$pin getNet]
        if {$n eq "NULL" || ![dict exists $netroots [$n getName]] || [dict get $netroots [$n getName]] ne $root} {
          error "OT_CORE_SCOPE_CTS_DOMAIN clock pin [[$pin getInst] getName]/[[$pin getMTerm] getName] left its root $root"
        }
      }
    }
    return $result
  }
}
