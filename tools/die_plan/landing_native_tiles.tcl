# Opt-in measured native dataflow placement. No net/cell/clock transformation.
set ::lnt_dir [file dirname [file normalize [info script]]]
uplevel #0 {
set lnt_b [ord::get_db_block]
set lnt_protected {}
set lnt_face [open [file join $::env(RESULTS_DIR) ot_face_flops.txt] r]
foreach lnt_line [split [read $lnt_face] \n] {
 set a [split $lnt_line \t]
 if {[llength $a]>1 && ![string match {cland:ring:*} [lindex $a 1]]} {dict set lnt_protected [lindex $a 0] 1}
}
close $lnt_face
proc lnt_graph {i} {
 set r [list [[$i getMaster] getName]]
 foreach t [$i getITerms] {
  if {[[$t getMTerm] getSigType] in {POWER GROUND}} continue
  set n [$t getNet]
  lappend r [list [[$t getMTerm] getName] [expr {$n eq "NULL" ? "-" : [$n getName]}]]
 }
 return [lsort $r]
}
set lnt_rows {}; set lnt_before {}; set lnt_held {}
set f [open [file join $::lnt_dir native_tiles_held.tsv] r]
foreach line [split [read $f] \n] {
 if {$line eq ""} continue
 lassign [split $line \t] n m
 set i [$lnt_b findInst $n]
 if {$i eq "NULL" || [[$i getMaster] getName] ne $m} {error "NATIVE_TILES missing held cell/master: $n"}
 dict set lnt_held $n [list [$i getLocation] [$i getOrient] [$i getPlacementStatus] [lnt_graph $i]]
}
close $f
set f [open [file join $::lnt_dir native_tiles_manifest.tsv] r]
foreach line [split [read $f] \n] {
 if {$line eq ""} continue
 lassign [split $line \t] n m bus tile
 if {[dict exists $lnt_before $n] || [dict exists $lnt_held $n] || [dict exists $lnt_protected $n]} {error "NATIVE_TILES duplicate/protected member: $n"}
 set i [$lnt_b findInst $n]
 if {$i eq "NULL" || [[$i getMaster] getName] ne $m || ![[$i getMaster] isCore]} {error "NATIVE_TILES stale mapped member/master: $n"}
 if {[$i getGroup] ne "NULL" && [$i getGroup] ne ""} {error "NATIVE_TILES existing group owns $n"}
 if {![regexp {^ft[0-9]+_i$} $bus] || ![string is integer -strict $tile] || $tile<0 || $tile>8} {error "NATIVE_TILES malformed tile"}
 if {[string first "u_cland_$bus/" [string map {\\ {}} $n]]<0} {error "NATIVE_TILES wrong native family: $n"}
 dict set lnt_before $n [lnt_graph $i]
 lappend lnt_rows $i
}
close $f
if {![llength $lnt_rows]} {error "NATIVE_TILES empty requested manifest"}
# All validation precedes mutation. Explicit external captures/status/controls
# remain outside the manifest and preserve their existing sites and clock phase.
foreach i $lnt_rows {$i setPlacementStatus PLACED}
dict for {n old} $lnt_before {
 if {[lnt_graph [$lnt_b findInst $n]] ne $old} {error "NATIVE_TILES input/output graph changed: $n"}
}
dict for {n old} $lnt_held {
 set i [$lnt_b findInst $n]
 if {[list [$i getLocation] [$i getOrient] [$i getPlacementStatus] [lnt_graph $i]] ne $old} {error "NATIVE_TILES held position/graph changed: $n"}
}
set f [open [file join $::env(RESULTS_DIR) native_tiles_applied.txt] w]
puts $f "unfixed [llength $lnt_rows] held [dict size $lnt_held] graph_changed 0 added_cycles 0"
close $f
puts "NATIVE_TILES unfixed [llength $lnt_rows] exact mapped data cells; held [dict size $lnt_held]; graph unchanged; cycles 0"
}
