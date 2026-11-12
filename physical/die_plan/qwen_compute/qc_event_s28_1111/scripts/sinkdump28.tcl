# QC-EVENT-S28 read-only (DIE-QC-97 sinkdump.tcl form, extended to clk_t<i> nets): every input ITerm on the die-clock
# nets clk / clk_t<i> of a placed odb (centre um, master, name, net); edge-clock fclk_* ring flops are on their own
# nets and so excluded.  Also: the hard-core (BLOCK master) instances (origin um, orient) and the die area.
read_db /odb/3_place.odb
set blk [ord::get_db_block]
set out [open /out/sinks.tsv w]
set n 0
set nets 0
foreach net [$blk getNets] {
  set nm [$net getName]
  if {![regexp {^clk(_t[0-9]+)?$} $nm]} continue
  incr nets
  foreach it [$net getITerms] {
    if {![$it isInputSignal]} continue
    set i [$it getInst]; set bb [$i getBBox]
    puts $out "[expr {([$bb xMin]+[$bb xMax])/2000.0}]\t[expr {([$bb yMin]+[$bb yMax])/2000.0}]\t[[$i getMaster] getName]\t[$i getName]\t$nm"
    incr n
  }
}
close $out
set co [open /out/cores.tsv w]
foreach i [$blk getInsts] {
  if {[[$i getMaster] getType] ne "BLOCK"} continue
  set bb [$i getBBox]
  puts $co "[$i getName]\t[[$i getMaster] getName]\t[expr {[$bb xMin]/1000.0}]\t[expr {[$bb yMin]/1000.0}]\t[$i getOrient]"
}
close $co
set da [$blk getDieArea]
set f [open /out/die.txt w]; puts $f "[expr {[$da xMin]/1000.0}] [expr {[$da yMin]/1000.0}] [expr {[$da xMax]/1000.0}] [expr {[$da yMax]/1000.0}]"; close $f
puts "S28 SINKS $n NETS $nets"
exit
