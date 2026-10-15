read_db /data/routes/gate/work/orfs/results/asap7/opentallas_ot_s81_hc_ctfx_reset_native_asap7_ref_gate/base/3_3_place_gp-failed.odb
set block [ord::get_db_block]
proc dump_state {prefix} {
 set b [ord::get_db_block]
 set c [open /data/${prefix}_cells.tsv w];set n [open /data/${prefix}_nets.tsv w];set p [open /data/${prefix}_ports.tsv w]
 foreach i [$b getInsts] {
  set bb [$i getBBox]
  puts $c "[$i getName]\t[[$i getMaster] getName]\t[$bb xMin]\t[$bb yMin]\t[$bb xMax]\t[$bb yMax]\t[$i getPlacementStatus]\t[$i getOrient]"
  foreach t [$i getITerms] {set net [$t getNet];set nm NULL;if {$net ne "NULL"} {set nm [$net getName]};puts $n "[$i getName]\t[[$t getMTerm] getName]\t$nm"}
 }
 foreach t [$b getBTerms] {
  set net [$t getNet];set nm NULL;if {$net ne "NULL"} {set nm [$net getName]}
  foreach pin [$t getBPins] {foreach bb [$pin getBoxes] {puts $p "[$t getName]\t[$t getIoType]\t$nm\t[[$bb getTechLayer] getName]\t[$bb xMin]\t[$bb yMin]\t[$bb xMax]\t[$bb yMax]"}}
 }
 close $c;close $n;close $p
}
set ot_pack_names {}
foreach path [glob /data/routes/gate/work/orfs/results/asap7/*/base/ot_inhold_firm.txt /data/routes/gate/work/orfs/results/asap7/*/base/ot_out_flop_at_pins.txt] {
 set f [open $path];foreach name [split [read $f] \n] {if {$name ne ""} {lappend ot_pack_names $name}};close $f
}
set f [open /data/owned_names.txt w];puts $f [join [lsort -unique $ot_pack_names] \n];close $f
set f [open /data/rows_exact.tsv w]
foreach row [$block getRows] {set bb [$row getBBox];puts $f "[$row getName]\t[$bb xMin]\t[$bb yMin]\t[$bb xMax]\t[$bb yMax]\t[$row getSpacing]\t[$row getOrient]"};close $f
dump_state before
source /data/anchor_capacity.tcl
dump_state after
write_db /data/capacity_candidate.odb
