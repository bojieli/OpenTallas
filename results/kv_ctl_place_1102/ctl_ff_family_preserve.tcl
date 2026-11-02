# Physical process only. Existing FFs remain DATA-touchable; CLOCK stays protected.
if {![info exists ::env(DONT_USE_CELLS)]} {set ::env(DONT_USE_CELLS) {}}
foreach family {DFFASRHQNx*_ASAP7_75t_R DFFHQNx*_ASAP7_75t_R} {
 if {$family ni $::env(DONT_USE_CELLS)} {lappend ::env(DONT_USE_CELLS) $family}
}
puts "CTL_DFF_FAMILY_PRESERVE physical new-master exclusions $::env(DONT_USE_CELLS)"
