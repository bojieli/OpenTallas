read_db /leaf/6_final.odb
set blk [ord::get_db_block]
set file [open /work/leaf_connectivity.tsv w]
puts $file "bterm\tnet\tinternal_iterms\thas_route"
set count 0;set bad 0
foreach bt [$blk getBTerms] {
 if {[$bt getSigType] in {POWER GROUND}} continue
 incr count
 set net [$bt getNet]
 if {$net eq "NULL"} {incr bad;continue}
 set terms [llength [$net getITerms]]
 set wire [expr {[$net getWire] ne "NULL"}]
 puts $file "[$bt getName]\t[$net getName]\t$terms\t$wire"
 if {$terms<1 || !$wire} {incr bad}
}
close $file
puts "LG_LEAF_CONNECTIVITY actual_signal_bterms=$count missing_internal_or_route=$bad"
if {$count!=1673 || $bad} {error "LG leaf disconnected signal"}
exit
