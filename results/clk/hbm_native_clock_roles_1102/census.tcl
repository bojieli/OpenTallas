read_db $::env(INPUT_ODB)
set block [ord::get_db_block]
set fh [open $::env(OUTPUT_TSV) w]
puts $fh "kind\troot\tnet\tinstance\tmaster\tpin\tsigtype\tiotype\tmastertype"
foreach bt [$block getBTerms] {
 set name [$bt getName]
 if {![string match clk* $name]} {continue}
 set net [$bt getNet]
 if {$net eq "NULL"} {puts $fh "ROOT\t$name\tUNCONNECTED\t\t\t\t\t[$bt getIoType]\t";continue}
 puts $fh "ROOT\t$name\t[$net getName]\t\t\t\t[$bt getSigType]\t[$bt getIoType]\t"
 foreach it [$net getITerms] {
  set inst [$it getInst]; set master [$inst getMaster]; set mt [$it getMTerm]
  puts $fh "ITERM\t$name\t[$net getName]\t[$inst getName]\t[$master getName]\t[$mt getName]\t[$mt getSigType]\t[$mt getIoType]\t[$master getType]"
 }
}
close $fh
puts "CLOCK_ROLE_CENSUS_DONE"
