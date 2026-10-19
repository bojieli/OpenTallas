# Source/port ownership for clock architecture. Derive from actual ordinary BTerm
# faces and true first sequential data endpoints / last sequential startpoints.
# Sequential copies remain actual distinct endpoints; no CTS name/seed/position
# of a register selects ownership. Asynchronous reset inputs are not data roots.
set ot_face_block [ord::get_db_block]
set ot_face_die [$ot_face_block getDieArea]
set ::ot_face_clock_owners {};set ::ot_face_clock_ports {}
set ot_face_data {};set ot_face_async {};set ot_face_regs {}
foreach c [all_registers -cells] {dict set ot_face_regs [get_full_name $c] $c}
foreach p [all_registers -async_pins] {dict set ot_face_async [get_full_name $p] 1}
foreach p [all_registers -data_pins] {set n [get_full_name $p];if {![dict exists $ot_face_async $n]} {dict set ot_face_data $n 1}}
foreach bt [$ot_face_block getBTerms] {
 if {[$bt getSigType] in {POWER GROUND CLOCK}} continue
 if {[llength [$bt getBPins]]!=1} {error "FACE_CLOCK missing/ambiguous BPin[$bt getName]"}
 set boxes [[lindex [$bt getBPins] 0] getBoxes]
 if {[llength $boxes]!=1} {error "FACE_CLOCK nonrectangular BPin[$bt getName]"}
 set box [lindex $boxes 0];set face {}
 if {[$box xMin]==[$ot_face_die xMin]} {set face W} elseif {[$box xMax]==[$ot_face_die xMax]} {set face E} elseif {[$box yMin]==[$ot_face_die yMin]} {set face S} elseif {[$box yMax]==[$ot_face_die yMax]} {set face N} else {error "FACE_CLOCK interior BPin[$bt getName]"}
 set port [get_ports -quiet [$bt getName]]
 if {[llength $port]!=1} {error "FACE_CLOCK unresolved ordinary port[$bt getName]"}
 set endpoints {}
 if {[$bt getIoType] eq "INPUT"} {
  foreach p [get_fanout -from $port -flat -endpoints_only -trace_arcs all] {
   set n [get_full_name $p]
   if {![dict exists $ot_face_data $n]} continue
   lappend endpoints [regsub {/[^/]+$} $n {}]
  }
 } elseif {[$bt getIoType] eq "OUTPUT"} {
  foreach p [get_fanin -to $port -flat -startpoints_only -trace_arcs all] {lappend endpoints [regsub {/[^/]+$} [get_full_name $p] {}]}
 } else {error "FACE_CLOCK unsupported inout[$bt getName]"}
 foreach n [lsort -unique $endpoints] {
  if {![dict exists $ot_face_regs $n]} continue
  dict set ::ot_face_clock_owners $n $face 1
  dict lappend ::ot_face_clock_ports $n [$bt getName]
 }
}
set ot_face_counts [dict create N 0 S 0 E 0 W 0];set ot_face_multi 0
foreach n [dict keys $::ot_face_clock_owners] {
 set faces [dict keys [dict get $::ot_face_clock_owners $n]]
 if {[llength $faces]>1} {incr ot_face_multi}
 foreach face $faces {dict incr ot_face_counts $face}
}
puts "SOURCE_FACE_CLOCK_OWNERS sequential_roots=[dict size $::ot_face_clock_owners] face_counts=$ot_face_counts shared_face_roots=$ot_face_multi derived_from_BTerm_and_native_sequential_graph=1"
