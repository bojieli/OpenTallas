# Read-only after the stock synth export. Ordered native stage rows claim an
# instance once. Earlier native rows with actual members can make a later row
# empty even when that later selector still matches the DB when run alone.
proc cland_native_selector_check {rows} {
 set names {}
 set ff_names {}
 foreach inst [[ord::get_db_block] getInsts] {
  set master [$inst getMaster]
  if {[$master isBlock]} continue
  set name [$inst getName]
  lappend names $name
  if {[string match DFF* [$master getName]]} {lappend ff_names $name}
 }
 cland_native_selector_ownership $rows $names $ff_names
}

proc cland_native_selector_ownership {rows names ff_names} {
 set claimed {}
 set by_name {}
 set by_ff_name {}
 set by_stem {}
 foreach name $names {dict set by_name $name 1}
 foreach name $ff_names {dict set by_ff_name $name 1}
 set shadowed 0
 set partial 0
 set missing 0
 foreach row $rows {
  lassign $row tag pattern ff_only exact stem
  if {[llength $exact]} {
   set index [expr {$ff_only ? $by_ff_name : $by_name}]
   set members {}
   foreach name [lsort -unique $exact] {
    if {[dict exists $index $name]} {lappend members $name}
   }
  } else {
   set candidates [expr {$ff_only ? $ff_names : $names}]
   if {$stem ne ""} {
    set key [list $ff_only $stem]
    if {![dict exists $by_stem $key]} {
     dict set by_stem $key [lsearch -all -inline -regexp $candidates $stem]
    }
    set candidates [dict get $by_stem $key]
   }
   set members [lsearch -all -inline -regexp $candidates $pattern]
  }
  if {![llength $members]} {
   # Placement still checks presence in the later, physically prepared DB.
   incr missing
   continue
  }
  set available 0
  set owners {}
  foreach name $members {
   if {[dict exists $claimed $name]} {
    dict incr owners [dict get $claimed $name]
   } else {
    dict set claimed $name $tag
    incr available
   }
  }
  if {!$available} {
   puts "OT_NATIVE_STAGE_SELECTOR SHADOWED $tag matched=[llength $members] owners={$owners}"
   incr shadowed
  } elseif {[dict size $owners]} {
   puts "OT_NATIVE_STAGE_SELECTOR PARTIAL $tag matched=[llength $members] available=$available"
   incr partial
  }
 }
 puts "OT_NATIVE_STAGE_SELECTOR checked=[llength $rows] claimed=[dict size $claimed] shadowed=$shadowed partial=$partial missing_at_synth=$missing"
 if {$shadowed} {error "OT_NATIVE_STAGE_SELECTOR $shadowed fully shadowed native stage selectors"}
}
