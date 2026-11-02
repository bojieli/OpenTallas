# Read Tcl command boundaries only; do not execute SDC or invoke STA.
proc commands {path} {
 set f [open $path r];set data [read $f];close $f
 set out {};set statement ""
 foreach line [split $data \n] {
  append statement $line \n
  if {![info complete $statement]} continue
  set s [string trim $statement];set statement ""
  if {$s eq "" || [string index $s 0] eq "#"} continue
  if {[regexp {^([A-Za-z_][A-Za-z_0-9:]*)} $s -> cmd]} {lappend out [list $cmd $s]}
 }
 if {[string trim $statement] ne ""} {error "incompleteSDC"}
 return $out
}
set root [file dirname [file normalize [info script]]]
set a [commands [file join $root final_grt.sdc]]
set b [commands [file join $root 4_cts.sdc]]
if {$a ne $b} {error "source/alias Tcl command parse differs"}
set counts {}
set relevant {}
foreach row $a {
 lassign $row cmd text
 if {[regexp {^(create_.*clock|set_clock_.*|set_false_path|set_multicycle_path|set_(max|min)_delay|set_(input|output)_delay)$} $cmd]} {
  dict incr counts $cmd
  lappend relevant $row
 }
}
set f [open [file join $root parsed_clock_exceptions.tcllist] w];puts $f $relevant;close $f
puts "PARSED_SDC_IDENTITY_PASS commands=[llength $a] timing_directives=[llength $relevant] counts=$counts"
