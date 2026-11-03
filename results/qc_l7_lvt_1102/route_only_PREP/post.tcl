# Save actual native route output before classification; preserve any failure.
write_db /route/actual_after_route.odb
set b [ord::get_db_block]
if {[llength [$b getInsts]] != [dict size $::l7_original]} {error "L7 DRT created/lost cells"}
set now {};foreach n [$b getNets] {lappend now [$n getName]}
if {[lsort $now] ne [lsort $::l7_nets]} {error "L7 DRT source net inventory changed"}
dict for {nm r} $::l7_original {
 set i [$b findInst $nm]
 if {$i eq "NULL" || [list [[$i getMaster] getName] [$i getLocation] [$i getOrient] [$i getPlacementStatus] [$i isDoNotTouch]] ne [lrange $r 0 4]} {error "L7 DRT source master/pose/status/DNT changed $nm"}
 dict for {pn nn} [lindex $r 5] {set t [$i findITerm $pn];set n [$t getNet];set current [expr {$n eq "NULL" ? "NULL" : [$n getName]}];if {$nn ne $current} {error "L7 DRT source incidence changed $nm/$pn"}}
}
ot_pg_require_bound l7_native_drt_post
puts L7_NATIVE_DRT_POST_SOURCE_PG_GUARD_PASS
