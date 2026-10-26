read_db /work/positive-final.odb
set blk [ord::get_db_block]
set leaf [$blk findInst u_leaf]
set file [open /work/connectivity.tsv w]
puts $file "iterm\tnet\tbterms\tother_iterms\thas_route"
set count 0;set bad 0
foreach it [$leaf getITerms] {
 if {[$it getSigType] in {POWER GROUND}} continue
 incr count
 set name [[$it getMTerm] getName]
 set net [$it getNet]
 if {$net eq "NULL"} {incr bad;continue}
 set bnames {};foreach bt [$net getBTerms] {lappend bnames [$bt getName]}
 set terms [llength [$net getITerms]]
 set wire [expr {[$net getWire] ne "NULL"}]
 puts $file "$name\t[$net getName]\t[join $bnames ,]\t$terms\t$wire"
 if {$bnames ne [list $name] || $terms!=1 || !$wire} {incr bad}
}
close $file
puts "LG_PARENT_CONNECTIVITY actual_signal_iterms=$count bad=$bad"
if {$count!=1673 || $bad} {error "LG parent connectivity failed"}
exit
