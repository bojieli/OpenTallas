read_db /data/4_cts.odb
set block [ord::get_db_block]
set count 0
set groups [dict create]
foreach inst [$block getInsts] {
 set master [$inst getMaster]
 set isseq 0
 foreach mt [$master getMTerms] {
  if {[$mt getName] in {CLK clk CK ck}} {set isseq 1; break}
 }
 if {!$isseq} continue
 incr count
 set name [$inst getName]
 set prefix [join [lrange [split $name /] 0 2] /]
 dict incr groups $prefix
}
puts "TOTAL_CLOCKED_INSTANCES $count"
dict for {name n} $groups {puts "CLOCK_PARTITION $n $name"}
exit
