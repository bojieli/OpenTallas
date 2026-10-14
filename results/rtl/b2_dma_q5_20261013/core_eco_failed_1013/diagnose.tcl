read_db /data/orfs/results/asap7/tile/base/6_final.odb
set block [ord::get_db_block]
foreach name {net19625 net19931 net21007 net21187 net22463 net24782} {
 set n [$block findNet $name]
 puts "NET $name"
 if {$n eq "NULL"} {puts "MISSING_ORIGINAL"; continue}
 puts "SIGTYPE [$n getSigType] ITCOUNT [llength [$n getITerms]] BTCOUNT [llength [$n getBTerms]]"
 foreach it [$n getITerms] {
  set inst [$it getInst];set mt [$it getMTerm];set bb [$inst getBBox]
  puts "PIN [$inst getName]/[$mt getName] MASTER [[$inst getMaster] getName] IO [$mt getIoType] AT [$bb xMin],[$bb yMin],[$bb xMax],[$bb yMax]"
 }
 foreach bt [$n getBTerms] {puts "BTERM [$bt getName] IO [$bt getIoType]"}
 puts "GUIDES [llength [$n getGuides]]"
}
exit
