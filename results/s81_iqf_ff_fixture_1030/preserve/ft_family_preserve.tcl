# Physical-process only; existing FFs remain touchable.
if {![info exists ::env(DONT_USE_CELLS)]} {set ::env(DONT_USE_CELLS) {}}
foreach family [list "DFFASRHQNx*_ASAP7_75t_R" "DFFHQNx*_ASAP7_75t_R"] {
  if {$family ni $::env(DONT_USE_CELLS)} {lappend ::env(DONT_USE_CELLS) $family}
}
puts "OT_FT_FAMILY_PRESERVE physical new-master exclusions $::env(DONT_USE_CELLS)"
