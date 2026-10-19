# Independent DB graph audit: count every physical BUF/INV from clk to every
# actual register clock and hard-memory clock, separately identifying native IO.
# No timing exception, clock mutation, geometry or functional behavior.
proc ot_gq_graph_visit {net depth} {
  if {[dict exists $::ot_gq_seen $net]} {
    if {[dict get $::ot_gq_seen $net] != $depth} {error "OT_GQ_CLOCK_RECONVERGENCE [$net getName]"}
    return
  }
  dict set ::ot_gq_seen $net $depth
  foreach it [$net getITerms] {
    if {![$it isInputSignal]} continue
    set inst [$it getInst]; set master [[$inst getMaster] getName]
    if {[regexp {^(BUF|INV|CKBUF|CKINV)} $master]} {
      dict incr ::ot_gq_bufs $master 1
      foreach out [$inst getITerms] {
        if {[$out isOutputSignal] && [$out getNet] ne "NULL"} {
          ot_gq_graph_visit [$out getNet] [expr {$depth + 1}]
        }
      }
    } elseif {[dict exists $::ot_gq_expected $it]} {
      if {[dict exists $::ot_gq_reached $it]} {error "OT_GQ_CLOCK_DUPLICATE [$it getName]"}
      dict set ::ot_gq_reached $it $depth
    } else {
      error "OT_GQ_CLOCK_UNKNOWN_LOAD [$inst getName]/[[$it getMTerm] getName] ($master)"
    }
  }
}
proc ot_gq_clock_graph {{allow_nonuniform 0}} {
  set block [ord::get_db_block]
  set ::ot_gq_expected {};set ::ot_gq_reached {};set ::ot_gq_seen {};set ::ot_gq_bufs {}
  set native {}
  foreach p [concat [get_fanout -from [all_inputs -no_clocks] -flat -endpoints_only] [get_fanin -to [all_outputs] -flat -startpoints_only]] {
    if {[catch {set ni [sta::sta_to_db_inst [$p instance]]}]} continue
    if {$ni ne "NULL"} {dict set native $ni 1}
  }
  foreach p [all_registers -clock [get_clocks core_clk] -clock_pins] {
    set inst [sta::sta_to_db_inst [$p instance]]
    set it [$inst findITerm [lindex [split [get_full_name $p] /] end]]
    if {$it eq "NULL"} {error "OT_GQ_CLOCK_NO_DB_PIN [get_full_name $p]"}
    dict set ::ot_gq_expected $it [list ff [dict exists $native [$it getInst]]]
  }
  set nm 0
  foreach inst [$block getInsts] {
    if {![[$inst getMaster] isBlock]} continue
    set cp [$inst findITerm clk]
    if {$cp eq "NULL"} {error "OT_GQ_CLOCK_NO_MACRO_CLK [$inst getName]"}
    dict set ::ot_gq_expected $cp [list macro 1];incr nm
  }
  if {$nm != 8} {error "OT_GQ_CLOCK_MACROS expected8 actual$nm"}
  set root [$block findBTerm clk]
  if {$root eq "NULL"} {error OT_GQ_CLOCK_NO_ROOT}
  ot_gq_graph_visit [$root getNet] 0
  set missing {};set ff {};set mc {};set io {}
  dict for {it tag} $::ot_gq_expected {
    if {![dict exists $::ot_gq_reached $it]} {lappend missing [$it getName];continue}
    set d [dict get $::ot_gq_reached $it]
    if {[lindex $tag 0] eq "macro"} {lappend mc $d} else {lappend ff $d}
    if {[lindex $tag 1]} {lappend io $d}
  }
  if {[llength $missing]} {error "OT_GQ_CLOCK_UNREACHED count=[llength $missing] sample=[lrange $missing 0 3]"}
  if {![llength $ff] || ![llength $io]} {error OT_GQ_CLOCK_EMPTY_NATIVE_SCOPE}
  set all [lsort -integer [concat $ff $mc]];set ios [lsort -integer $io];set ms [lsort -integer $mc]
  set mn [lindex $all 0];set mx [lindex $all end]
  set nb 0;dict for {k v} $::ot_gq_bufs {incr nb $v}
  puts "OT_GQ_CLOCK_GRAPH sinks=[llength $all] flops=[llength $ff] macros=[llength $mc] native_io_clocks=[llength $io] stages=$mn..$mx native=[lindex $ios 0]..[lindex $ios end] macro=[lindex $ms 0]..[lindex $ms end] buffers=$nb inventory=$::ot_gq_bufs"
  if {$mn != $mx} {
    puts OT_GQ_CLOCK_GRAPH_NONUNIFORM
    if {!$allow_nonuniform} {error "OT_GQ_CLOCK_GRAPH unequal actual stage counts $mn/$mx"}
  } else {puts OT_GQ_CLOCK_GRAPH_PASS}
}
