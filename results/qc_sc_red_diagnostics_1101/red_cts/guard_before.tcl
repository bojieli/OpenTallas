# Save the actual rebound input state, then run the normal pre-CTS hook.
set ::red_guard_block [ord::get_db_block]
proc red_cells {} {set d {};foreach i [$::red_guard_block getInsts] {dict set d [$i getName] [list [[$i getMaster] getName] [$i getLocation] [$i getOrient] [$i getPlacementStatus] [$i isDoNotTouch]]};return $d}
proc red_incidence {} {set d {};foreach i [$::red_guard_block getInsts] {foreach t [$i getITerms] {set n [$t getNet];set nn NULL;if {$n ne "NULL"} {set nn [$n getName]};dict set d [list [$i getName] [[$t getMTerm] getName]] $nn}};return $d}
proc red_terms {} {set d {};foreach p [$::red_guard_block getBTerms] {set n [$p getNet];set nn NULL;if {$n ne "NULL"} {set nn [$n getName]};dict set d [$p getName] [list [$p getIoType] [$p getSigType] $nn]};return $d}
proc red_nets {} {set d {};foreach n [$::red_guard_block getNets] {dict set d [$n getName] [list [$n getSigType] [$n isSpecial] [$n isDoNotTouch]]};return $d}
set ::red_before_cells [red_cells];set ::red_before_inc [red_incidence];set ::red_before_terms [red_terms];set ::red_before_nets [red_nets]
set ff 0;set nodes 0;foreach i [$::red_guard_block getInsts] {if {[string match DFF* [[$i getMaster] getName]]} {incr ff};if {[string match mp_ck_* [$i getName]]} {incr nodes}}
if {$ff!=34225 || $nodes!=8269} {error "RED_CTS_INPUT_NATIVE_CENSUS $ff $nodes"}
# Protect the existing legal DATA placement during the native CTS DPL.
foreach i [$::red_guard_block getInsts] {if {[$i getPlacementStatus] eq "PLACED"} {$i setPlacementStatus FIRM}}
source /work/fc_dt_lift_cts.tcl
