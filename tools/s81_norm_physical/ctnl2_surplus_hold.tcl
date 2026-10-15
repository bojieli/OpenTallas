# Physical-only successor to immutable CLOSED CTNL2 np2-granted-57b4f1931.
# Removes one measured surplus serial hold cell, preserving every sequential cell,
# clock, pin, boundary hold pad, and all SDC checks. Re-route and qualify afresh.
set block [ord::get_db_block]
set inst [$block findInst hold12489]
if {$inst == "NULL"} {error "CTNL2 ECO: expected hold12489 absent"}
if {[[$inst getMaster] getName] ne "HB2xp67_ASAP7_75t_R"} {error "CTNL2 ECO: unexpected master"}
set input NULL
set output NULL
foreach pin [$inst getITerms] {
  set direction [[$pin getMTerm] getIoType]
  if {$direction eq "INPUT"} {set input $pin}
  if {$direction eq "OUTPUT"} {set output $pin}
}
if {$input eq "NULL" || $output eq "NULL"} {error "CTNL2 ECO: bad buffer terminals"}
set upstream [$input getNet]
set downstream [$output getNet]
set srcs {}
foreach pin [$upstream getITerms] {
  if {$pin ne $input && [[$pin getMTerm] getIoType] eq "OUTPUT"} {lappend srcs [[$pin getInst] getName]}
}
set dsts {}
foreach pin [$downstream getITerms] {
  if {$pin ne $output} {lappend dsts [[$pin getInst] getName]}
}
if {$srcs ne "ot_ihdrv_00291" || $dsts ne "hold7244" || [llength [$downstream getBTerms]]} {
  error "CTNL2 ECO connectivity differs: sources=$srcs destinations=$dsts"
}
foreach pin [$downstream getITerms] {if {$pin ne $output} {$pin connect $upstream}}
odb::dbInst_destroy $inst
odb::dbNet_destroy $downstream
puts "CTNL2_ECO bypass hold12489 only: ot_ihdrv_00291 -> hold7244; no sequential or clock changes"
