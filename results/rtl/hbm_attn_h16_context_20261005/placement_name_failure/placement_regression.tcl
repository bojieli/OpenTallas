read_db /in/results/asap7/opentallas_ot_attn_tile_m6h1_asap7_codex_h16_nb5_context_r1/base/2_1_floorplan.odb
source /diag/placement_corrected.tcl
set b [ord::get_db_block]
set n 0
foreach i [$b getInsts] {if {[[$i getMaster] getName] eq "ot_attn_hgrp_m6h1"} {incr n; puts "PLACED=[$i getName] LOC=[$i getLocation] STATUS=[$i getPlacementStatus]"; if {[$i getPlacementStatus] ne "FIRM"} {error "Macro moved/unfixed"}}}
if {$n != 16} {error "Not full H16"}
puts "PASS16_SELECTED_FIXED_HEADS"
exit
