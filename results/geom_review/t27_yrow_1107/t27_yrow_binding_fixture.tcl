# Usage: tclsh fixture.tcl exact_CTS_yrow.tsv
set re {^u_bound[.]g_u_lf0_u_vp_yrow_d[.].*native_memory[^0-9]*[0-2][^0-9]+([0-9]+)[^0-9]}
set f [open [lindex $argv 0] r];set txt [read $f];close $f
set groups [dict create];set total 0
foreach line [split [string trim $txt] "\n"] {
 set n [lindex [split $line "\t"] 2]
 if {![regexp -- $re $n -> g]} {error "fixture missed $n"}
 dict incr groups $g;incr total
}
if {$total != 384 || [dict size $groups] != 128} {error "binding count"}
dict for {g n} $groups {if {$n != 3} {error "group size $g=$n"}}
foreach n {{u_bound.g_u_lf0_u_vp_ly.\native_memory[1][85]$_DFF_P_} {u_bound.g_u_lf0_u_vp_yrow_d.\native_other[1][85]$_DFF_P_} {u_bound.g_u_lf0_u_vp_yrow_d.\native_memory[3][85]$_DFF_P_}} {
 if {[regexp -- $re $n]} {error "scope negative matched"}
}
puts "PASS384 exact bindings,128 groups of3,3 scope negatives"
