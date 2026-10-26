read_db [lindex [glob /work/results/asap7/*/base/6_final.odb] 0]
set blk [ord::get_db_block]
set f [open /untimed.txt r];set names [split [string trim [read $f]] \n];close $f
set o [open /work/c13_untimed_witness.tsv w]
puts $o "pin\tdirection\tnet\tdrivers\tloads"
foreach name $names {
 set b [$blk findBTerm $name]
 if {$b eq "NULL"} {error "missing actual port $name"}
 set net [$b getNet]
 if {$net eq "NULL"} {puts $o "$name\t[$b getIoType]\tNULL\tNONE\t0";continue}
 set drivers {};set loads 0
 foreach it [$net getITerms] {
  if {[$it getIoType] eq "INPUT"} {incr loads}
  if {[$it getIoType] eq "OUTPUT"} {lappend drivers "[[[$it getInst] getMaster] getName]:[[$it getInst] getName]/[[$it getMTerm] getName]"}
 }
 puts $o "$name\t[$b getIoType]\t[$net getName]\t[join $drivers ,]\t$loads"
}
close $o
puts "C13_UNTIMED_WITNESS [llength $names] actual6final ports"
exit
