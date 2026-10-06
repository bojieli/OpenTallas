# Post-insertion binding to retained finite fences, based on real sink ancestry.
# Invoke before EACH CTS/repair detailed_placement. No change to timing or padding.
proc ot_w2_sink_domains {initial} {
 set queue $initial; set seen [dict create]; set domains [dict create]
 while {[llength $queue]} {
  set net [lindex $queue 0]; set queue [lrange $queue 1 end]
  if {$net eq "NULL"} {continue}
  set name [$net getName]
  if {[dict exists $seen $name]} {continue}
  dict set seen $name 1
  foreach bt [$net getBTerms] {
   if {[$bt getIoType] eq "OUTPUT"} {
    set domain w2_inherited
    if {[$bt getName] in {reserve_r source_permit retained done}} {set domain w2_child}
    dict set domains $domain 1
   }
  }
  foreach it [$net getITerms] {
   if {[[$it getMTerm] getIoType] ne "INPUT"} {continue}
   set inst [$it getInst]; set group [$inst getGroup]
   if {$group ne "NULL"} {
    set gn [$group getName]
    if {$gn ni {w2_inherited w2_child w2_gateway}} {error "Foreign sink region $gn"}
    dict set domains $gn 1
    continue
   }
   foreach out [$inst getITerms] {
    if {[[$out getMTerm] getIoType] eq "OUTPUT"} {lappend queue [$out getNet]}
   }
  }
 }
 return [dict keys $domains]
}
set ot_block [ord::get_db_block]
set ot_groups [dict create]
foreach ot_g [$ot_block getGroups] {
 if {[$ot_g getName] in {w2_inherited w2_child w2_gateway}} {dict set ot_groups [$ot_g getName] $ot_g}
}
if {[dict size $ot_groups]!=3} {error "Missing retained finite W2 fences"}
set ot_assignments {}; set ot_clock_count 0; set ot_repair_count 0; set ot_shared_count 0
# Resolve all ancestry BEFORE adding any new member; avoid order-dependent inference.
foreach ot_i [$ot_block getInsts] {
 if {[$ot_i isFixed] || [$ot_i getGroup] ne "NULL"} {continue}
 set ot_clock_nets {}; set ot_outputs {}; set ot_output_count 0
 foreach ot_t [$ot_i getITerms] {
  set ot_n [$ot_t getNet]
  if {$ot_n ne "NULL" && [$ot_n getSigType] eq "CLOCK"} {lappend ot_clock_nets $ot_n}
  if {[[$ot_t getMTerm] getIoType] eq "OUTPUT"} {
   incr ot_output_count
   if {$ot_n ne "NULL"} {lappend ot_outputs $ot_n}
  }
 }
 if {$ot_output_count==0} {continue}; # Retained physical-only cells.
 if {[llength $ot_clock_nets]} {
  set ot_domains [ot_w2_sink_domains $ot_clock_nets]; incr ot_clock_count
 } else {
  set ot_domains [ot_w2_sink_domains $ot_outputs]; incr ot_repair_count
 }
 if {![llength $ot_domains]} {error "No bounded logical sink ancestry for [$ot_i getName]"}
 set ot_domain w2_inherited
 if {[llength $ot_domains]==1} {set ot_domain [lindex $ot_domains 0]}
 if {[llength $ot_domains]>1} {incr ot_shared_count}; # Common body-root branch feeds both retained fences.
 lappend ot_assignments [list $ot_i $ot_domain]
}
foreach ot_pair $ot_assignments {
 lassign $ot_pair ot_i ot_domain
 [dict get $ot_groups $ot_domain] addInst $ot_i
}
puts "OT_W2_POST_INSERTION_MEMBERSHIP clock=$ot_clock_count repair=$ot_repair_count shared=$ot_shared_count"
