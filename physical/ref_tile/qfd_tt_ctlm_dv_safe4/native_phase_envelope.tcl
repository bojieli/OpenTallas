# Read-only diagnostic. Source only after actual propagated CTS/parasitic timing.
# Never changes SDC, exceptions, source phase, uncertainty, or path constraints.
foreach key {OT_NATIVE_PHASE_OUT OT_NATIVE_PHASE_SOURCE OT_NATIVE_PHASE_CORNER} {
 if {![info exists ::env($key)] || $::env($key) eq ""} {error "NATIVE_PHASE missing $key"}
}
if {$::env(OT_NATIVE_PHASE_CORNER) ni {tt ff}} {error "NATIVE_PHASE requires actual TT or FF scene"}
if {![regexp {^[0-9a-f]{40}$} $::env(OT_NATIVE_PHASE_SOURCE)]} {error "NATIVE_PHASE source must be exact commit"}
foreach kind {min max} {find_timing_paths -path_delay $kind -group_path_count 1 -endpoint_path_count 1}
set np_scene [get_property [sta::cmd_scene] name]
set np_out [open $::env(OT_NATIVE_PHASE_OUT) w]
puts $np_out "source\tcorner\tscene\tclock\tpin\tmin_ps\tmax_ps\tliberty"
set np_count 0
foreach clock [all_clocks] {
 set cname [get_full_name $clock]
 set waveform {}; foreach t [$clock waveform] {lappend waveform [sta::time_sta_ui $t]}
 if {[llength $waveform]!=2} {error "NATIVE_PHASE invalid waveform"}
 foreach pin [all_registers -clock $cname -clock_pins] {
  set np_libs {}
  foreach lc [get_lib_cells -of_objects [get_cells -of_objects $pin]] {
   set np_lib [get_full_name $lc]
   if {![regexp -nocase {_(tt|ff|ss)/|_(tt|ff|ss)_} $np_lib -> np_corner np_alt]} {error "NATIVE_PHASE unknown actual Liberty corner $np_lib"}
   if {$np_corner eq ""} {set np_corner $np_alt}
   if {[string tolower $np_corner] ne $::env(OT_NATIVE_PHASE_CORNER)} {error "NATIVE_PHASE actual Liberty corner differs from receipt label: $np_lib"}
   lappend np_libs $np_lib
  }
  if {![llength $np_libs]} {error "NATIVE_PHASE actual clock sink lacks Liberty association"}
  set bounds {}
  foreach kind {min max} {
   set values {}
   foreach vertex [$pin vertices] {
    if {$vertex eq "NULL"} continue
    foreach transition {rise fall} marker {^ v} {
     set paths [$vertex path_iterator $transition $kind]
     while {[$paths has_next]} {
      set path [$paths next]; set tag [$path tag]; set edge [lindex $tag 4]
      if {[lindex $tag 1] ne $np_scene || [lindex $tag 2] ne "${marker}${kind}" || [lindex $tag 3] ne $cname || $edge ni {^ v} || [string first "(clock prop)" $tag]<0} continue
      set a [sta::time_sta_ui [$path arrival]]
      if {![string is double -strict $a] || [regexp -nocase {inf|nan} $a]} {error "NATIVE_PHASE nonfinite clock tag"}
      lappend values [expr {$a-[lindex $waveform [expr {$edge eq "^"?0:1}]]}]
     }
     $paths finish
    }
   }
   if {![llength $values]} {error "NATIVE_PHASE missing propagated $kind clock tag $cname/[get_full_name $pin]"}
   set ordered [lsort -real $values]
   lappend bounds [expr {$kind eq "min"?[lindex $ordered 0]:[lindex $ordered end]}]
  }
  puts $np_out "$::env(OT_NATIVE_PHASE_SOURCE)\t$::env(OT_NATIVE_PHASE_CORNER)\t$np_scene\t$cname\t[get_full_name $pin]\t[lindex $bounds 0]\t[lindex $bounds 1]\t[join $np_libs ,]"
  incr np_count
 }
}
close $np_out
if {$np_count==0} {error "NATIVE_PHASE no sequential clock sinks"}
puts "NATIVE_PHASE DIAGNOSTIC rows=$np_count source=$::env(OT_NATIVE_PHASE_SOURCE) corner=$::env(OT_NATIVE_PHASE_CORNER) no_constraint_change=1"
