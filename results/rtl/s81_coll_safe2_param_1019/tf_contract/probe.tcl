read_db /work/results/asap7/opentallas_dsfd_coll_lane_w_asap7_ref_gate/base/3_place.odb
set b [ord::get_db_block]
foreach name {tf {tf[0]} ck {ck[0]}} {
 set p [$b findBTerm $name]
 if {$p eq "NULL" || $p eq ""} {continue}
 set net [$p getNet]
 puts "TF_CONTRACT_PORT $name io=[$p getIoType] signal=[$p getSigType] net=[$net getName] iterms=[llength [$net getITerms]] bterms=[llength [$net getBTerms]]"
 foreach bp [$net getBTerms] {puts "TF_CONTRACT_PEER_PORT [$bp getName] io=[$bp getIoType] signal=[$bp getSigType]"}
 foreach ip [$net getITerms] {
  if {[[$ip getMTerm] getIoType] ne "OUTPUT"} {continue}
  set inst [$ip getInst]
  puts "TF_CONTRACT_DRIVER [$inst getName]/[[$ip getMTerm] getName] master=[[$inst getMaster] getName] location=[$inst getLocation]"
 }
}
puts "TF_CONTRACT_PRECTS_PROBE_DONE"
exit
