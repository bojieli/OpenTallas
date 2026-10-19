set f [open report.tcldict]; set r [read $f]; close $f
set p [dict get $r native_pg]
set groups [dict create]
set names [dict create]
foreach failure [dict get $p failures] {
 set key {}
 foreach field {master pin role actual_net actual_role expected_net reason} {lappend key [dict get $failure $field]}
 dict incr groups $key
 dict set names [dict get $failure instance] 1
}
set f [open grouped_summary.tcldict w]
puts $f [dict create status [dict get $r status] checked [dict get $p checked] failure_count [dict get $p failure_count] roles [dict get $p roles] groups $groups affected_instances [dict size $names] rules [dict get $r declared_native_rules]]
close $f
set f [open failure_names.txt w]; dict for {n v} $names {puts $f $n}; close $f
puts "GROUPED checked=[dict get $p checked] failures=[dict get $p failure_count] instances=[dict size $names]"
