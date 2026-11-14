if {![info exists ::env(DESIGN_NAME)] || $::env(DESIGN_NAME) ne "dsdv_gunit_l1f_bf"} {error "GF5_LOCALITY wrong module or missing exact module context; A1 needs its own reviewed S-face form"}
# PRIVATE GF5 early-GPL producer-locality; no logical/timing constraint edits.
# Source the kit's original face/macro landing hook before this file.
proc gf5_make_regions {} {
 set blk [ord::get_db_block]
 set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
 set owners [dict create]; set captures [dict create]; set todo [dict create]; set specs [dict create]
 foreach i [$blk getInsts] {
  if {![[$i getMaster] isCore]} continue
  set n [string map {\\ ""} [$i getName]]; set owner ""; set cap 0
  if {[string match svreg_* $n] && ![string match svreg_data* $n]} {puts "GF5_META_NODE $n [[$i getMaster] getName]"}
  if {[regexp {^svreg_data\[([0-9]+)\]} $n -> bit]} {set owner READ[format %02d [expr {$bit/32}]];set cap 1}
  if {[regexp {^svreg_(v|f|l|bn|lv)(\[|\$|$)} $n]} {set owner META;set cap 1}
  if {[regexp {^sc\[([0-9]+)\]} $n -> bit]} {set owner READ[format %02d [expr {($bit%512)/32}]]}
  if {[regexp {^g_e\[([0-9]+)\]} $n -> lane]} {set owner READ[format %02d [expr {$lane%16}]]}
  if {[regexp {^g_fw\[([0-9]+)\]} $n -> lane]} {set owner READ[format %02d $lane]}
  if {[regexp {(^|[./])s_bias_svreg\[([0-9]+)\]} $n]} {set owner BIAS;set cap 1}
  if {$owner ne ""} {
   dict set owners $i $owner
   if {$cap && [string match *DFF* [[$i getMaster] getName]]} {dict incr captures $owner}
  } elseif {![string match *DFF* [[$i getMaster] getName]] && [$i getPlacementStatus] ni {FIRM LOCKED}} {dict set todo $i 1}
 }
 # Backward data-cone membership only; do not cross unrelated register boundaries.
 set edges [dict create]
 foreach net [$blk getNets] {
  if {[$net getSigType] in {POWER GROUND CLOCK}} continue
  set terms [$net getITerms]
  if {[llength $terms]>65} continue
  set ds {};set ls {}
  foreach t $terms {
   set i [$t getInst]
   if {![[$i getMaster] isCore]} continue
   if {[[$t getMTerm] getIoType] eq "OUTPUT"} {lappend ds $i} else {lappend ls $i}
  }
  foreach d $ds {foreach l $ls {if {$d ne $l} {dict lappend edges $d $l}}}
 }
 for {set round 0} {$round<100 && [dict size $todo]} {incr round} {
  set add [dict create]
  dict for {i unused} $todo {
   if {![dict exists $edges $i]} continue
   set os [dict create]
   foreach l [dict get $edges $i] {if {[dict exists $owners $l]} {dict set os [dict get $owners $l] 1}}
   # Shared comb stays ungrouped rather than arbitrarily choosing a lane.
   if {[dict size $os]==1} {dict set add $i [lindex [dict keys $os] 0]}
  }
  if {![dict size $add]} break
  dict for {i o} $add {dict set owners $i $o;dict unset todo $i}
 }
 set ndata 0;set nmeta 0;set nbias 0
 dict for {o c} $captures {
  if {[string match READ* $o]} {incr ndata $c} elseif {$o eq "META"} {incr nmeta $c} elseif {$o eq "BIAS"} {incr nbias $c}
 }
 if {$ndata} {
  if {$ndata!=512 || $nmeta!=22 || $nbias} {error "GF5_CAPTURE_COUNT expected F512+22 got $ndata+$nmeta bias$nbias"}
  for {set l 0} {$l<16} {incr l} {
   set x [expr {8.64+43.2*($l%4)}];set y [expr {5.4+40.5*($l/4)}]
   dict set specs READ[format %02d $l] [list $x $y [expr {$x+40.5}] [expr {$y+37.8}]]
  }
  dict set specs META {183.6 60.48 226.8 103.68}
 } else {
  if {$nbias!=256} {error "GF5_CAPTURE_COUNT expected A256 got bias$nbias F$ndata+$nmeta"}
  dict set specs BIAS {149.04 54.0 192.24 97.2}
 }
 set fh [open /work/gf5_region_members.csv w];puts $fh "region,name,master,area_um2,fixed"
 dict for {o box} $specs {
  lassign $box x0 y0 x1 y1
  set ms {};set area 0.;set fixed 0.
  dict for {i label} $owners {
   if {$label ne $o} continue
   set a [expr {double([[$i getMaster] getWidth])*[[$i getMaster] getHeight]/$dbu/$dbu}]
   set f [expr {[$i getPlacementStatus] in {FIRM LOCKED}}]
   puts $fh "$o,[$i getName],[[$i getMaster] getName],$a,$f"
   if {!$f} {lappend ms $i;set area [expr {$area+$a}]}
  }
  foreach i [$blk getInsts] {
   if {![[$i getMaster] isCore] || [$i getPlacementStatus] ni {FIRM LOCKED}} continue
   set b [$i getBBox];set dx [expr {min($x1,double([$b xMax])/$dbu)-max($x0,double([$b xMin])/$dbu)}];set dy [expr {min($y1,double([$b yMax])/$dbu)-max($y0,double([$b yMin])/$dbu)}]
   if {$dx>0 && $dy>0} {set fixed [expr {$fixed+$dx*$dy}]}
  }
  set fill [expr {($area+$fixed)/(($x1-$x0)*($y1-$y0))}]
  puts "GF5_REGION $o captures[dict get $captures $o] movable[llength $ms] area$area fixed$fixed fill$fill box$box"
  if {$fill>=0.4} {error "GF5_REGION_CAPACITY $o fill $fill >= PLACE_DENSITY0.4"}
  set reg [odb::dbRegion_create $blk ot_gf5_$o];$reg setRegionType INCLUSIVE
  odb::dbBox_create $reg [expr {round($x0*$dbu)}] [expr {round($y0*$dbu)}] [expr {round($x1*$dbu)}] [expr {round($y1*$dbu)}]
  set g [odb::dbGroup_create $reg ot_gf5_$o];$g setType VOLTAGE_DOMAIN
  foreach i $ms {$g addInst $i}
 }
 close $fh
 puts "GF5_CAPTURE_TOTAL data$ndata meta$nmeta bias$nbias; combinational propagation stops at unrelated DFFs; fixed faces preserved"
}
rename global_placement ::gf5_original_global_placement
proc global_placement {args} {gf5_make_regions;uplevel 1 [linsert $args 0 ::gf5_original_global_placement]}
