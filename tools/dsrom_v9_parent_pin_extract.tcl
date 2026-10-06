# Literal mapped connectivity, read-only completed parent synthesis database.
read_db /input/1_synth.odb
set file [open /out/cell_pins.tsv w]
puts $file "instance\tmaster\tpin\tio\tnet"
foreach inst [[ord::get_db_block] getInsts] {
 foreach term [$inst getITerms] {
  set net [$term getNet]
  if {$net eq "NULL"} {continue}
  set mt [$term getMTerm]
  puts $file "[$inst getName]\t[[$inst getMaster] getName]\t[$mt getName]\t[$mt getIoType]\t[$net getName]"
 }
}
close $file
set file [open /out/ports.tsv w]
puts $file "port\tio\tnet"
foreach term [[ord::get_db_block] getBTerms] {
 set net [$term getNet]
 if {$net eq "NULL"} {continue}
 puts $file "[$term getName]\t[$term getIoType]\t[$net getName]"
}
close $file
puts OT_PARENT_LITERAL_CONNECTIVITY_EXTRACT_PASS
