read_db /in/6_final.odb
set block [ord::get_db_block]
set f [open /out/alias_collisions.tsv w]
set renamed 0
foreach bt [$block getBTerms] {
 if {[$bt getIoType] ne "OUTPUT"} {continue}
 set pname [$bt getName]
 set actual [$bt getNet]
 set collision [$block findNet $pname]
 if {$collision ne "NULL" && $collision ne $actual} {
  puts $f "$pname\t[$actual getName]\t[$collision getName]\t[llength [$collision getITerms]]"
  $collision rename __physical_preout_$pname
  incr renamed
 }
}
close $f
puts "CANONICAL_OUTPUT_ALIAS_RENAMES $renamed"
write_verilog /out/6_final_canonical.v
exit
