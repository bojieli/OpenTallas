set b [ord::get_db_block]
dict for {nm r} $::l1_route_original {
 set i [$b findInst $nm];l1_route_need [expr {$i ne "NULL"}] "lost source instance $nm"
 l1_route_need [expr {[list [[$i getMaster] getName] [$i getLocation] [$i getOrient] [$i getPlacementStatus] [$i isDoNotTouch]] eq [lrange $r 0 4]}] "source master/pose/status/DNT changed $nm"
 dict for {pn nn} [lindex $r 5] {set t [$i findITerm $pn];set n [$t getNet];set now [expr {$n eq "NULL" ? "NULL" : [$n getName]}];l1_route_need [expr {$nn eq $now}] "source connection changed $nm/$pn"}
}
set ca {};foreach n [$b getNets] {if {[$n getSigType] ne "CLOCK"} continue;foreach t [$n getITerms] {lappend ca [list [$n getName] [[$t getInst] getName] [[$t getMTerm] getName]]}}
l1_route_need [expr {[lsort $::l1_route_clock] eq [lsort $ca]}] {CLOCK source graph changed}
ot_pg_connect_all l1_route_post
ot_pg_require_bound l1_route_post
puts L1_NATIVE_DRT_POST_SOURCE_CLOCK_GUARD_PASS
