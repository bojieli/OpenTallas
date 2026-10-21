# SUPERSEDED by c486a646c halfcycle landing model. DO NOT source as a physical kit.
error "Superseded hash cohort fence model: bind actual mapped halfcycle owners first"
# Candidate physical binding only; source97fd22a11, model e94f5f1e5.
# Install before GPL, retain through DPL/CTS. Empty/misbound groups fail closed.
set b [ord::get_db_block]
set dbu [$b getDbUnitsPerMicron]
set hc_boxes [dict create seedmain {302.4 43.2 561.6 108.0} rolls {367.2 216.0 388.8 237.6} rolln {388.8 216.0 410.4 237.6}]
for {set g 0} {$g<6} {incr g} {
 set x [expr {194.4+129.6*($g%3)}];set y [expr {129.6+108*($g/3)}]
 dict set hc_boxes group$g [list $x $y [expr {$x+129.6}] [expr {$y+86.4}]]
}
set hc_groups {};set hc_count {};set hc_area {}
dict for {key box} $hc_boxes {
 set region [odb::dbRegion_create $b hc_$key]
 lassign $box x0 y0 x1 y1
 odb::dbBox_create $region [expr {round($x0*$dbu)}] [expr {round($y0*$dbu)}] [expr {round($x1*$dbu)}] [expr {round($y1*$dbu)}]
 dict set hc_groups $key [odb::dbGroup_create $region hc_$key]
 dict set hc_count $key 0;dict set hc_area $key 0
}
foreach i [$b getInsts] {
 regsub -all {\\} [$i getName] {} name
 set key {}
 if {[regexp {(^|[./])u_e[./]u_hash[./]u_group([0-5])[./]} $name unused prefix group]} {
  set key group$group
 } elseif {[regexp {(^|[./])u_e[./]u_hash[./]u_seed[./]} $name]} {
  set key seedmain
  if {[regexp {[./]u_n[01]_[01]_[123][./]} $name]} {
   set key rolln
  } elseif {[regexp {DFF} [[$i getMaster] getName]]} {
   # Existing roll_s flop owners use actual Q-net semantics; no assumed generated cell name.
   foreach it [$i getITerms] {
    if {[$it getIoType] ne "OUTPUT" || [$it getNet] eq "NULL"} continue
    regsub -all {\\} [[$it getNet] getName] {} qname
    if {[regexp {[./]u_seed[./]roll_s_[01]_[123](\[|$)} $qname]} {set key rolls}
   }
  }
 }
 if {$key eq {}} continue
 if {[[$i getMaster] isBlock]} {error "Hash cohort unexpectedly includes macro $name"}
 [dict get $hc_groups $key] addInst $i
 dict incr hc_count $key
 dict set hc_area $key [expr {[dict get $hc_area $key]+double([[$i getMaster] getWidth])*[[$i getMaster] getHeight]/$dbu/$dbu}]
}
dict for {key group} $hc_groups {
 set n [dict get $hc_count $key]
 if {$n==0} {error "Hash cohort empty: $key; exact source/hierarchy mismatch"}
 lassign [dict get $hc_boxes $key] x0 y0 x1 y1
 set area [dict get $hc_area $key];set boxarea [expr {($x1-$x0)*($y1-$y0)}]
 if {$area>$boxarea} {error "Hash cohort $key mapped cell area $area exceeds box $boxarea"}
 puts [format "HASH_COHORT_BOUND %s cells=%d mapped_area=%.5f box_area=%.5f fill=%.4f" $key $n $area $boxarea [expr {$area/$boxarea}]]
}
# NOT a capacity/placement/clock PASS. Actual legal-row capacity, complete-cell bounds,
# DPL legality and postCTS reset/removal/clock spread must still be measured.
