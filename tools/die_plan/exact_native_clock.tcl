# Default OFF. Defines a PREP consumer only; never invokes CTS, placement or save.
# Caller must load actual native libs/ODB/flat PG rules and the canonical native
# PG birth helper, then explicitly enable this consumer and pin its data SHA.
namespace eval ::ot_enc {}
proc ::ot_enc::dbu {v} {
  variable units
  set n [expr {round($v*$units)}]
  if {abs($v*$units-$n)>1e-5} {error "OT_ENC_NONREPRESENTABLE_DBU $v"}
  return $n
}
proc ::ot_enc::rect {box} {return [list [$box xMin] [$box yMin] [$box xMax] [$box yMax]]}
proc ::ot_enc::rect_dbu {box} {return [lmap v $box {::ot_enc::dbu $v}]}
proc ::ot_enc::hit {a b} {
  lassign $a x y z t;lassign $b u v w q
  return [expr {$x<$w && $u<$z && $y<$q && $v<$t}]
}
proc ::ot_enc::master_pin_rect {master pin} {
  set mt [$master findMTerm $pin]
  if {$mt eq "NULL"} {error "OT_ENC_MASTER_PIN $pin"}
  set x0 1e99;set y0 1e99;set x1 -1e99;set y1 -1e99;set count 0
  foreach mp [$mt getMPins] {
    foreach b [$mp getGeometry] {
      set x0 [expr {min($x0,[$b xMin])}];set y0 [expr {min($y0,[$b yMin])}]
      set x1 [expr {max($x1,[$b xMax])}];set y1 [expr {max($y1,[$b yMax])}];incr count
    }
  }
  if {!$count} {error "OT_ENC_MASTER_PIN_NO_METAL $pin"}
  return [list $x0 $y0 $x1 $y1]
}
proc ::ot_enc::source_reconnect {it target} {
  set i [$it getInst];set protected [$i isDoNotTouch]
  if {$protected} {$i setDoNotTouch 0}
  try {
    $it disconnect;$it connect $target
    if {[$it getNet] ne $target} {error OT_ENC_CLOCK_CONNECT_NOT_EFFECTIVE}
  } finally {if {$protected} {$i setDoNotTouch 1}}
}
proc ::ot_enc::apply {data_file birth_module} {
  if {![info exists ::env(OT_EXACT_NATIVE_CLOCK_PLAN)] || $::env(OT_EXACT_NATIVE_CLOCK_PLAN) ne "1"} {
    return [dict create status DISABLED_EXACT_NATIVE_CLOCK_CONSUMER]
  }
  foreach command {ot_pg_native_birth_begin ot_pg_native_birth_end ot_pg_assert_all_native ot_pg_prepare} {
    if {[info commands ::$command] eq ""} {error "OT_ENC_NATIVE_PG_API_REQUIRED $command"}
  }
  if {[info commands ::ot_native_pg_status] ne "" && [dict get [ot_native_pg_status] active]} {error OT_ENC_NESTED_NATIVE_BIRTH_REFUSED}
  if {![info exists ::env(OT_EXACT_NATIVE_CLOCK_PLAN_SHA256)] ||
      ![regexp {^[0-9a-f]{64}$} $::env(OT_EXACT_NATIVE_CLOCK_PLAN_SHA256)]} {error OT_ENC_DATA_SHA_REQUIRED}
  set digest [lindex [exec sha256sum -- $data_file] 0]
  if {$digest ne $::env(OT_EXACT_NATIVE_CLOCK_PLAN_SHA256)} {error OT_ENC_DATA_SHA_MISMATCH}
  source $data_file
  if {$::ot_enc_schema ne "opentallas.exact_native_clock.prep.v1"} {error OT_ENC_SCHEMA}
  foreach {key expected} [list OT_VCLK_TT $::ot_enc_tt_ps OT_VCLK_FF $::ot_enc_ff_ps] {
    if {![info exists ::env($key)] || ![string is double -strict $::env($key)] ||
        abs($::env($key)-$expected)>1e-9} {error "OT_ENC_NATIVE_BUDGET_MISMATCH $key"}
  }
  variable units
  set block [ord::get_db_block];set units [$block getDbUnitsPerMicron]
  set expected_outline [rect_dbu [concat {0 0} $::ot_enc_outline]]
  if {[rect [$block getDieArea]] ne $expected_outline} {error OT_ENC_OUTLINE_MISMATCH}
  set bt [$block findBTerm clk]
  if {$bt eq "NULL" || [$bt getIoType] ne "INPUT"} {error OT_ENC_SINGLE_PRIMARY_CLOCK}
  set root [$bt getNet]
  if {$root eq "NULL" || [llength [$root getBTerms]]!=1 || [$root isDoNotTouch]} {error OT_ENC_PRIMARY_CLOCK_NOT_OPEN}
  # Entry shapes are checked, never moved. No delivered reset identity changes.
  foreach entry $::ot_enc_entries {
    lassign $entry name x0 y0 x1 y1;set bterm [$block findBTerm $name]
    if {$bterm eq "NULL" || [$bterm getIoType] ne "INPUT"} {error "OT_ENC_ENTRY $name"}
    set boxes {}
    foreach bp [$bterm getBPins] {foreach box [$bp getBoxes] {
      if {[[$box getTechLayer] getName] ne "M5"} {error "OT_ENC_ENTRY_LAYER $name"}
      lappend boxes [rect $box]
    }}
    if {[llength $boxes]!=1 || [lindex $boxes 0] ne [rect_dbu [list $x0 $y0 $x1 $y1]]} {error "OT_ENC_ENTRY_POSE $name"}
  }
  set master [[ord::get_db] findMaster BUFx24_ASAP7_75t_R]
  if {$master eq "NULL" || [$master getWidth] != [dbu 1.62] || [$master getHeight] != [dbu .27]} {error OT_ENC_NATIVE_ROOT_MASTER}
  if {[master_pin_rect $master Y] ne [rect_dbu {.310 .027 1.602 .243}]} {error OT_ENC_NATIVE_ROOT_OUTPUT_METAL}
  if {[master_pin_rect $master A] ne [rect_dbu {.018 .027 .078 .243}]} {error OT_ENC_NATIVE_ROOT_INPUT_METAL}
  set poses {};set rectangles {};set expected [dict create];set terms {};set ff 0;set sram 0
  foreach sink $::ot_enc_sinks {
    lassign $sink name cell pin kind owner x0 y0 x1 y1
    set inst [$block findInst $name]
    if {$inst eq "NULL" || [[$inst getMaster] getName] ne $cell || ![$inst isPlaced]} {error "OT_ENC_NATIVE_SINK_MASTER_POSE $name"}
    if {$kind eq "FF"} {
      if {[[$inst getMaster] isBlock] || [$inst getOrient] ni {R0 MX}} {error "OT_ENC_NATIVE_FF_ORIENTATION $name"};incr ff
    } elseif {$kind eq "SRAM"} {
      if {![[$inst getMaster] isBlock] || [$inst getOrient] ne "R0"} {error "OT_ENC_NATIVE_SRAM_ORIENTATION $name"};incr sram
    } else {error "OT_ENC_NATIVE_SINK_KIND $kind"}
    set it [$inst findITerm $pin]
    if {$it eq "NULL" || [[$it getMTerm] getSigType] ne "CLOCK" || [$it getNet] ne $root} {error "OT_ENC_TYPED_PRIMARY_CLOCK_SINK $name/$pin"}
    if {[dict exists $expected $it]} {error "OT_ENC_DUPLICATE_CLOCK_SINK $name/$pin"}
    if {$owner<0 || $owner>=[llength $::ot_enc_roots]} {error OT_ENC_ROOT_INDEX}
    set box [rect [$it getBBox]]
    if {$box ne [rect_dbu [list $x0 $y0 $x1 $y1]]} {error "OT_ENC_NATIVE_CLOCK_PIN_POSE $name/$pin"}
    dict set expected $it $owner;lappend terms [list $it $root]
  }
  if {$ff!=$::ot_enc_expected_ff || $sram!=$::ot_enc_expected_sram} {error OT_ENC_TYPED_INVENTORY}
  set actual [lsort [$root getITerms]]
  if {$actual ne [lsort [dict keys $expected]]} {error OT_ENC_UNENUMERATED_PRIMARY_CLOCK_ENDPOINT}
  foreach macro $::ot_enc_macros {
    lassign $macro name x0 y0 x1 y1;set inst [$block findInst $name]
    if {$inst eq "NULL" || ![[$inst getMaster] isBlock] ||
        [rect [$inst getBBox]] ne [rect_dbu [list $x0 $y0 $x1 $y1]]} {error "OT_ENC_NATIVE_MACRO_POSE $name"}
  }
  foreach row $::ot_enc_roots {
    lassign $row name cell x0 y0 x1 y1 reservation_id
    if {[$block findInst $name] ne "NULL" || [$block findNet ${name}_out] ne "NULL"} {error "OT_ENC_OWNED_NAMESPACE_ALREADY_EXISTS $name"}
    set b [rect_dbu [list $x0 $y0 $x1 $y1]];lassign $b x y z t
    set orientation ""
    foreach r [$block getRows] {
      lassign [$r getOrigin] rx ry;set rb [$r getBBox];set sw [[$r getSite] getWidth]
      if {$ry!=$y || $x<[$rb xMin] || $z>[$rb xMax] || $t>[$rb yMax] || ($x-$rx)%$sw} continue
      if {[$r getOrient] ni {R0 MX}} {error "OT_ENC_ROOT_ROW_ORIENTATION $name"}
      if {$orientation ne "" && $orientation ne [$r getOrient]} {error "OT_ENC_AMBIGUOUS_NATIVE_ROW $name"}
      set orientation [$r getOrient]
    }
    if {$orientation eq ""} {error "OT_ENC_NO_EXACT_NATIVE_ROW $name"}
    foreach previous $rectangles {if {[hit $b $previous]} {error "OT_ENC_ROOT_ROOT_BODY $name"}}
    lappend rectangles $b;lappend poses [list $name $x $y $orientation $b $reservation_id]
  }
  set counts [lrepeat [llength $poses] 0]
  dict for {it owner} $expected {
    lset counts $owner [expr {[lindex $counts $owner]+1}]
    lassign [lindex $rectangles $owner] x y z t
    set a [list [expr {$x+[dbu .310]}] [expr {$y+[dbu .027]}] [expr {$x+[dbu 1.602]}] [expr {$y+[dbu .243]}]]
    set b [rect [$it getBBox]];set far 0
    foreach xx [list [lindex $a 0] [lindex $a 2]] {foreach yy [list [lindex $a 1] [lindex $a 3]] {
      foreach u [list [lindex $b 0] [lindex $b 2]] {foreach v [list [lindex $b 1] [lindex $b 3]] {
        set far [expr {max($far,abs($xx-$u)+abs($yy-$v))}]
      }}
    }}
    if {$far>$::ot_enc_radius_um*$units+1e-6*$units} {error "OT_ENC_PREFLIGHT_ACTUAL_OUTPUT_TO_CLK_RADIUS [[$it getInst] getName]"}
  }
  foreach count $counts {if {$count<1 || $count>1500} {error OT_ENC_LOCAL_MODEL_CAPACITY}}
  set root_island [rect_dbu $::ot_enc_root_island]
  # Inspect all current placed standard cells, including COMB logic. A model
  # reservation is not permission to overlap cells that occupied it during GPL.
  foreach inst [$block getInsts] {
    if {![$inst isPlaced]} {error "OT_ENC_UNPLACED_NATIVE_CELL [$inst getName]"}
    set b [rect [$inst getBBox]]
    if {[[$inst getMaster] isBlock]} {
      lassign $b a c d e;set h [dbu 4.32]
      set b [list [expr {$a-$h}] [expr {$c-$h}] [expr {$d+$h}] [expr {$e+$h}]]
    }
    foreach p $rectangles {if {[hit $b $p]} {error "OT_ENC_ROOT_OCCUPIED [$inst getName]"}}
    if {[hit $b $root_island]} {error "OT_ENC_ROOT_ISLAND_OCCUPIED [$inst getName]"}
  }
  # Only source-pinned, exact, native hard-blockage reservations may be
  # consumed. Foreign blockages remain obstacles, including reuse cutouts.
  set owned_reservations [dict create]
  foreach bk [$block getBlockages] {
    if {[$bk isSoft] || [$bk getMaxDensity]>0} continue
    set b [rect [$bk getBBox]]
    set prop [odb::dbStringProperty_find $bk ot_exact_native_clock_reservation]
    set id "";if {$prop ne "NULL"} {set id [$prop getValue]}
    foreach pose $poses {
      lassign $pose name x y orient planned expected_id
      if {$id eq $expected_id} {
        if {$b ne $planned || [dict exists $owned_reservations $id]} {error "OT_ENC_RESERVATION_POSE_OR_DUPLICATE $name"}
        dict set owned_reservations $id [list $bk $b]
      } elseif {[hit $b $planned]} {error "OT_ENC_FOREIGN_HARD_BLOCKAGE $name"}
    }
  }
  if {[dict size $owned_reservations]!=[llength $poses]} {error OT_ENC_EXACT_SOURCE_RESERVATIONS_REQUIRED}
  # All geometry/source checks above precede every native creation/reconnect.
  set born {};set nets {};set reconnected {};set consumed {};set active 0;set ended 0
  set code [catch {
    ot_pg_native_birth_begin $birth_module;set active 1
    set status [ot_native_pg_status]
    if {![dict get $status active] || [dict get $status contract] ne "native_pg_birth.flat_literal.v1" ||
        [dict get $status block_id] != [$block getId] ||
        [dict get $status database_id] != [[$block getDataBase] getId]} {error OT_ENC_NATIVE_BIRTH_CONTEXT}
    dict for {id record} $owned_reservations {
      lassign $record bk box
      # Log before destroy for whole-body rollback on a native exception.
      lappend consumed [list $id $box];odb::dbBlockage_destroy $bk
    }
    foreach pose $poses {
      lassign $pose name x y orient b
      set inst [odb::dbInst_create $block $master $name];lappend born $inst
      $inst setOrient $orient;$inst setLocation $x $y;$inst setPlacementStatus FIRM
      if {[rect [$inst getBBox]] ne $b} {error "OT_ENC_NATIVE_ROOT_LOCATION_CHANGED $name"}
      set net [odb::dbNet_create $block ${name}_out];lappend nets $net;$net setSigType CLOCK
      [$inst findITerm A] connect $root;[$inst findITerm Y] connect $net
    }
    dict for {it owner} $expected {
      # Log BEFORE disconnect so a failed connect is rolled back too.
      lappend reconnected $it;source_reconnect $it [lindex $nets $owner]
    }
    set expected_primary {};set local_members [dict create]
    for {set j 0} {$j<[llength $born]} {incr j} {
      set inst [lindex $born $j];set n [lindex $nets $j]
      if {[[$inst findITerm A] getNet] ne $root || [[$inst findITerm Y] getNet] ne $n} {error OT_ENC_NATIVE_ROOT_CONNECT_NOT_EFFECTIVE}
      lappend expected_primary [$inst findITerm A]
      dict set local_members $j [list [$inst findITerm Y]]
    }
    dict for {it owner} $expected {dict lappend local_members $owner $it}
    if {[lsort [$root getITerms]] ne [lsort $expected_primary]} {error OT_ENC_PRIMARY_MEMBERSHIP_AFTER_INSTALL}
    dict for {owner members} $local_members {
      if {[lsort [[lindex $nets $owner] getITerms]] ne [lsort $members]} {error "OT_ENC_LOCAL_MEMBERSHIP_AFTER_INSTALL $owner"}
    }
    # Recheck actual inserted Y full metal against actual target CLK metal.
    set limit [expr {$::ot_enc_radius_um*$units+1e-6*$units}]
    dict for {it owner} $expected {
      set buf [lindex $born $owner];set a [rect [[$buf findITerm Y] getBBox]];set b [rect [$it getBBox]]
      set far 0
      foreach x [list [lindex $a 0] [lindex $a 2]] {foreach y [list [lindex $a 1] [lindex $a 3]] {
        foreach u [list [lindex $b 0] [lindex $b 2]] {foreach v [list [lindex $b 1] [lindex $b 3]] {
          set far [expr {max($far,abs($x-$u)+abs($y-$v))}]
        }}
      }}
      if {$far>$limit} {error "OT_ENC_ACTUAL_OUTPUT_TO_CLK_RADIUS [[$it getInst] getName]"}
    }
    try {ot_pg_native_birth_end} finally {set active 0}
    set ended 1
    if {[dict get [ot_native_pg_status] active]} {error OT_ENC_NATIVE_BIRTH_STILL_ATTACHED}
    ot_pg_assert_all_native $block [ot_pg_prepare $block]
    # No post-hoc PG repair, no detailed placement and no CTS. All clock nets
    # stay open; only these actual constructor-bound clock driver poses freeze.
    foreach inst $born {$inst setDoNotTouch 1}
  } result options]
  if {$code} {
    set cleanup {}
    foreach it $reconnected {if {[catch {source_reconnect $it $root} why]} {lappend cleanup $why}}
    # Include a factory-created instance even if its constructor threw before
    # returning a Tcl handle. Namespace was empty at preflight and is ours only.
    foreach pose $poses {
      set i [$block findInst [lindex $pose 0]]
      if {$i ne "NULL"} {if {[catch {$i setDoNotTouch 0;odb::dbInst_destroy $i} why]} {lappend cleanup $why}}
    }
    foreach pose $poses {
      set n [$block findNet [lindex $pose 0]_out]
      if {$n ne "NULL"} {if {[catch {odb::dbNet_destroy $n} why]} {lappend cleanup $why}}
    }
    foreach reservation $consumed {
      lassign $reservation id box
      if {[catch {
        set surviving {}
        foreach candidate [$block getBlockages] {
          set prop [odb::dbStringProperty_find $candidate ot_exact_native_clock_reservation]
          if {$prop ne "NULL" && [$prop getValue] eq $id} {lappend surviving $candidate}
        }
        if {![llength $surviving]} {
          set bk [odb::dbBlockage_create $block {*}$box]
          odb::dbStringProperty_create $bk ot_exact_native_clock_reservation $id
        } elseif {[llength $surviving]!=1 || [rect [[lindex $surviving 0] getBBox]] ne $box} {
          error "OT_ENC_RESERVATION_ROLLBACK_AMBIGUOUS $id"
        }
      } why]} {lappend cleanup $why}
    }
    if {$active} {if {[catch {ot_pg_native_birth_end} why]} {lappend cleanup $why};set active 0}
    if {[catch {
      if {[info commands ot_native_pg_status] eq ""} {error OT_ENC_NATIVE_BIRTH_STATUS_MISSING}
      set status [ot_native_pg_status]
      if {![dict exists $status active] || [dict get $status active] ne "0"} {error "OT_ENC_NATIVE_BIRTH_NOT_PROVEN_INACTIVE $status"}
    } why]} {lappend cleanup $why}
    if {[catch {ot_pg_assert_all_native $block [ot_pg_prepare $block]} why]} {lappend cleanup $why}
    if {[llength $cleanup]} {append result "\nOT_ENC_ROLLBACK_OR_PG_CLEANUP_FAILED $cleanup; discard process, never save"}
    # Native callbacks or Tcl wrappers may propagate return/break/continue.
    # Every nonzero body completion remains an explicit failure after rollback.
    if {$code!=1} {
      set result "OT_ENC_UNEXPECTED_COMPLETION code=$code result=$result"
      dict set options -errorcode [list OT_ENC UNEXPECTED_COMPLETION $code]
    }
    dict set options -code 1;dict set options -level 0
    return -options $options $result
  }
  return [dict create status EXACT_NATIVE_CLOCK_CONSUMER_PREP_INSTALLED_UNQUALIFIED roots [llength $born] FF $ff SRAM $sram \
    added_data_FF 0 added_data_cycles 0 PG_callback_active 0 CTS_dispatched 0]
}
