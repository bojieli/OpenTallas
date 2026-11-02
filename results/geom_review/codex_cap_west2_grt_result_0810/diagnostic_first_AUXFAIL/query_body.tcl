# Diagnostic only: immutable currentA source, no resizer, placement or routing.
set target [get_pins {fa_kh$_DFF_P_/D}]
if {[llength $target] != 1} {error "CAP_PRICE receiver identity"}
foreach pin {A1 A2 B C} {
 set p [get_pins _27646_/$pin]
 if {[llength $p] != 1} {error "CAP_PRICE missing input $pin"}
 foreach kind {max min} {
  puts "CAP_PATH_BEGIN $pin $kind"
  set paths [find_timing_paths -through $p -to $target -path_delay $kind -group_path_count 1 -endpoint_path_count 1]
  if {![llength $paths]} {error "CAP_PRICE no path $pin $kind"}
  foreach path $paths {
   puts "CAP_PATH $pin $kind [get_property $path slack] [get_full_name [get_property $path startpoint]] [get_full_name [get_property $path endpoint]]"
   foreach point [get_property $path points] {
    set pname [get_full_name [get_property $point pin]]
    puts "CAP_POINT $pin $kind [list $pname] [get_property $point arrival]"
    puts "CAP_POINT_NET $pin $kind [list $pname] [list [get_full_name [get_nets -quiet -of_objects [list [get_property $point pin]]]]]"
   }
  }
  report_checks -through $p -to $target -path_delay $kind -group_path_count 1 -endpoint_path_count 1 -format full_clock_expanded -fields {slew cap fanout} -digits 4
  puts "CAP_PATH_END $pin $kind"
 }
}
set block [ord::get_db_block]
foreach name {_27646_/A1 _27646_/A2 _27646_/B _27646_/C _27646_/Y wire17963/A wire17963/Y lweco_219418/A lweco_219418/Y} {
 set p [get_pins $name]
 set n [get_nets -of_objects $p]
 set loads [get_pins -of_objects $n -filter direction==input]
 puts "CAP_LOADS [list $name] [get_full_name $n] [llength $loads] [list [get_full_name $loads]]"
 set slash [string last / $name];set i [$block findInst [string range $name 0 $slash-1]];set it [$i findITerm [string range $name $slash+1 end]]
 if {![catch {$it getAvgXY} xy]} {puts "CAP_AVGXY [list $name] $xy"} else {puts "CAP_AVGXY_UNAVAILABLE [list $name] [list $xy]"}
}
puts "CAP_QUERY_DONE 4"
