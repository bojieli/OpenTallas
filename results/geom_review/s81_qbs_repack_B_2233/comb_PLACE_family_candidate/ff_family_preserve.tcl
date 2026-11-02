# Disabled candidate physical new-master exclusions, same mechanism as FT_FULL_STAGE family preservation.
# Existing FFs stay FIRM and touchable only to permit normal input buffering. Synthesis config is untouched.
if {![info exists ::env(DONT_USE_CELLS)]} {set ::env(DONT_USE_CELLS) {}}
foreach family {DFFHQNx*_ASAP7_75t_R DFFASRHQNx*_ASAP7_75t_R} {
 if {$family ni $::env(DONT_USE_CELLS)} {lappend ::env(DONT_USE_CELLS) $family}
}
puts "HIST_FF_FAMILY_PRESERVE new-master exclusions $::env(DONT_USE_CELLS)"
