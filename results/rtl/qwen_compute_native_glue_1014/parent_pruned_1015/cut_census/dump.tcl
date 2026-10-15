read_db /work/results/asap7/opentallas_qfd_tile_nk_banked_v1_asap7_ref_gate/base/3_2_place_iop.odb
set b [ord::get_db_block]
set f [open /out/connections.tsv w]
foreach n [$b getNets] {
 set name [$n getName]
 set typ [$n getSigType]
 foreach t [$n getITerms] {
 set i [$t getInst]
 set m [$i getMaster]
 puts $f "$name	$typ	[$i getName]	[$m getName]	[[$t getMTerm] getName]	[$t getIoType]"
 }
 foreach t [$n getBTerms] {puts $f "$name	$typ	@PARENT	@PARENT	[$t getName]	[$t getIoType]"}
}
close $f
set f [open /out/instances.tsv w]
foreach i [$b getInsts] {
 set m [$i getMaster]
 puts $f "[$i getName]	[$m getName]	[$m getWidth]	[$m getHeight]"
}
close $f
puts QCE_CUT_DUMP_COMPLETE
exit
