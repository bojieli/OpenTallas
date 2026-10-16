set odbfile [lindex [glob /work/results/asap7/*/base/6_final.odb] 0]
read_db $odbfile
set block [ord::get_db_block]
foreach name {{fv_in[5]} {tid[7]} {tid[6]}} {
 set bt [$block findBTerm $name]
 if {$bt eq "NULL"} {error "unused proof: missing actual BTerm $name"}
 if {[$bt getIoType] ne "INPUT"} {error "unused proof: $name not input"}
 set net [$bt getNet]
 set n 0
 if {$net ne "NULL"} {set n [llength [$net getITerms]]}
 if {$n != 0} {error "unused proof: $name has $n actual mapped ITerm loads"}
 puts "UNUSED_INPUT_ZERO_LOAD name=$name iterms=$n"
}
puts "XS_UNUSED_INPUT_PROOF_PASS ports=3"
exit
