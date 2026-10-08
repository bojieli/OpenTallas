read_db /in/results/asap7/opentallas_ot_su12_sfu_asap7_hub_m12sfu/base/6_final.odb
set block [ord::get_db_block]
foreach bt [$block getBTerms] {
 set net [$bt getNet]
 set cells {}
 if {$net != "NULL"} {foreach it [$net getITerms] {lappend cells [[$it getInst] getMaster]}}
 set types {}
 foreach cell $cells {lappend types [$cell getName]}
 puts "OT_PIN|[$bt getName]|[$bt getIoType]|[$bt getSigType]|[llength $cells]|[join [lsort -unique $types] ,]"
}
exit
