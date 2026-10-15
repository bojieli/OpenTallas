read_db /work/results/asap7/opentallas_qwen_tx_rne_r1_asap7_ref_gate/base/3_2_place_iop.odb
set b [ord::get_db_block]
puts "QCE_DBU [$b getDbUnitsPerMicron]"
foreach t [$b getBTerms] {
 if {[$t getSigType] == "POWER" || [$t getSigType] == "GROUND"} {continue}
 foreach pin [$t getBPins] {
  foreach box [$pin getBoxes] {
   puts "QCE_PIN	[$t getName]	[$t getIoType]	[[$box getTechLayer] getName]	[$box xMin]	[$box yMin]	[$box xMax]	[$box yMax]"
  }
 }
}
exit
