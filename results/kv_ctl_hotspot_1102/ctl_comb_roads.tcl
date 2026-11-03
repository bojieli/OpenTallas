# Same ordinary INCLUSIVE GPL-region API as zone_fence.tcl. No instance is fixed,
# resized or inserted here. Normal port buffering runs before this deferred hook.
proc ot_ctl_comb_roads_create {} {
  if {[info exists ::ot_ctl_roads_created]} {return}
  set b [ord::get_db_block]
  set u [expr {double([$b getDbUnitsPerMicron])}]
  set da [$b getDieArea]
  if {abs(double([$da xMax])/$u-233.28)>0.001 || abs(double([$da yMax])/$u-302.4)>0.001} {error "CTL_COMB_ROAD wrong reviewed outline"}
  set ff 0; set clock_insts [dict create]; set clock_nets [dict create]; set todo {}
  foreach i [$b getInsts] {
    if {[regexp {^(DFF|DHL|DLL|SDF|ASYNC)} [[$i getMaster] getName]]} {
      if {[$i getPlacementStatus] ni {FIRM LOCKED}} {error "CTL_COMB_ROAD FF not already protected [$i getName]"}
      incr ff
    }
    foreach t [$i getITerms] {
      set mt [$t getMTerm]
      if {[$mt getSigType] eq "CLOCK" || [regexp {^(CLK|CK|GCLK)$} [$mt getName]]} {
        set n [$t getNet]; if {$n ne "NULL"} {lappend todo $n}
      }
    }
  }
  if {$ff!=18768} {error "CTL_COMB_ROAD wrong FF inventory $ff"}
  while {[llength $todo]} {
    set n [lindex $todo end]; set todo [lrange $todo 0 end-1]
    if {[dict exists $clock_nets $n]} continue
    dict set clock_nets $n 1
    foreach t [$n getITerms] {
      if {![$t isOutputSignal]} continue
      set i [$t getInst]; set mn [[$i getMaster] getName]
      if {[regexp {^(DFF|DHL|DLL|SDF|ASYNC)} $mn] || [[$i getMaster] isBlock]} continue
      dict set clock_insts $i 1
      foreach it [$i getITerms] {
        if {[[$it getMTerm] getIoType] eq "OUTPUT"} continue
        set ni [$it getNet]; if {$ni ne "NULL" && [$ni getSigType] ni {POWER GROUND}} {lappend todo $ni}
      }
    }
  }
  set labels [dict create]; set seed_area [dict create]
  foreach row $::ot_ctl_road_seeds {
    lassign $row name master zn
    set i [$b findInst $name]
    if {$i eq "NULL" || [[$i getMaster] getName] ne $master} {error "CTL_COMB_ROAD exact seed mismatch $name"}
    if {[$i getPlacementStatus] in {FIRM LOCKED} || [dict exists $clock_insts $i] || [[$i getMaster] isBlock] || [regexp {^(DFF|DHL|DLL|SDF|ASYNC)} $master]} {error "CTL_COMB_ROAD seed is protected $name"}
    dict set labels $i $zn
  }
  if {[dict size $labels]!=2212} {error "CTL_COMB_ROAD seed count [dict size $labels]"}
  # Only already-existing ordinary BUF trees whose complete downstream frontier
  # is in one guide may inherit it. Shared/broadcast/clock buffers remain free.
  set added 0
  for {set round 0} {$round<100} {incr round} {
    set found [dict create]
    foreach i [$b getInsts] {
      if {[dict exists $labels $i] || [dict exists $clock_insts $i] || [$i getPlacementStatus] in {FIRM LOCKED} || ![regexp {^BUF} [[$i getMaster] getName]]} continue
      set votes [dict create]; set blocked 0; set loads 0
      foreach ot [$i getITerms] {
        if {![$ot isOutputSignal]} continue
        set n [$ot getNet]; if {$n eq "NULL" || [dict exists $clock_nets $n]} {set blocked 1;continue}
        foreach t [$n getITerms] {
          if {[$t isOutputSignal]} continue
          set l [$t getInst]; incr loads
          if {![dict exists $labels $l]} {set blocked 1} else {dict set votes [dict get $labels $l] 1}
        }
        foreach bt [$n getBTerms] {if {[$bt getIoType] ne "INPUT"} {set blocked 1}}
      }
      if {!$blocked && $loads && [dict size $votes]==1} {dict set found $i [lindex [dict keys $votes] 0]}
    }
    if {![dict size $found]} break
    dict for {i zn} $found {dict set labels $i $zn;incr added}
  }
  foreach row $::ot_ctl_road_spec {
    lassign $row zn x0 y0 x1 y1 reserve_cell_area
    set members {}; set cell_area 0.; set buf_area 0.; set fixed 0.;set row_area 0.
    dict for {i label} $labels {
      if {$label ne $zn} continue
      lappend members $i
      set a [expr {double([[$i getMaster] getWidth])*[[$i getMaster] getHeight]/$u/$u}]
      if {[regexp {^BUF} [[$i getMaster] getName]]} {set buf_area [expr {$buf_area+$a}]} else {set cell_area [expr {$cell_area+$a}]}
    }
    foreach rr [$b getRows] {
      set bb [$rr getBBox];set xx0 [expr {max($x0,double([$bb xMin])/$u)}];set xx1 [expr {min($x1,double([$bb xMax])/$u)}];set yy0 [expr {max($y0,double([$bb yMin])/$u)}];set yy1 [expr {min($y1,double([$bb yMax])/$u)}]
      if {$xx1>$xx0 && $yy1>$yy0} {set row_area [expr {$row_area+($xx1-$xx0)*($yy1-$yy0)}]}
    }
    foreach i [$b getInsts] {
      if {![[$i getMaster] isCore] || [$i getPlacementStatus] ni {FIRM LOCKED}} continue
      set bb [$i getBBox];set xx0 [expr {max($x0,double([$bb xMin])/$u)}];set xx1 [expr {min($x1,double([$bb xMax])/$u)}];set yy0 [expr {max($y0,double([$bb yMin])/$u)}];set yy1 [expr {min($y1,double([$bb yMax])/$u)}]
      if {$xx1>$xx0 && $yy1>$yy0} {set fixed [expr {$fixed+($xx1-$xx0)*($yy1-$yy0)}]}
    }
    set need [expr {$fixed+($cell_area+max($buf_area,$reserve_cell_area))/0.6}]
    if {$need>=$row_area || ![llength $members]} {error "CTL_COMB_ROAD native row capacity $zn need=$need rows=$row_area"}
    set rn ot_ctl_comb_road_$zn
    if {[$b findRegion $rn] ne "NULL"} {error "CTL_COMB_ROAD unexpected existing region $rn"}
    set reg [odb::dbRegion_create $b $rn];$reg setRegionType INCLUSIVE
    odb::dbBox_create $reg [expr {round($x0*$u)}] [expr {round($y0*$u)}] [expr {round($x1*$u)}] [expr {round($y1*$u)}]
    set group [odb::dbGroup_create $reg $rn];$group setType VOLTAGE_DOMAIN
    foreach i $members {$group addInst $i}
    puts "CTL_COMB_ROAD $zn seeds_area=$cell_area existing_buf_area=$buf_area reserve_cell_area=$reserve_cell_area fixed_area=$fixed row_area=$row_area members=[llength $members]"
  }
  set ::ot_ctl_roads_created 1
  puts "CTL_COMB_ROAD_CREATED seeds=2212 existing_ordinary_BUF_members=$added FF_moves=0 clock_moves=0 inserted_cells=0"
}
rename global_placement ::ot_ctl_roads_previous_global_placement
proc global_placement {args} {
  ot_ctl_comb_roads_create
  uplevel 1 [linsert $args 0 ::ot_ctl_roads_previous_global_placement]
}
