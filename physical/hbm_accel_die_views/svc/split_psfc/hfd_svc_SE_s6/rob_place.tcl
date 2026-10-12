# hfd_svc_SE_s6: per-PC ROB macro placement (gen_svc_seg.py, tputx-svc); halo = MACRO_PLACE_HALO
set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
proc ot_rob_strip {n} { return [string map {\\ {}} $n] }
set nrob 0
set hit 0; foreach i [$b getInsts] { if {[[$i getMaster] getName] eq "ot_sram_1r1w_128x256_m1_r2c2" && [string match "*u_pc26?u_rob*" [ot_rob_strip [$i getName]]]} { $i setOrient R0; $i setLocation [expr {round(41.472 * $dbu)}] [expr {round(25.92 * $dbu)}]; $i setPlacementStatus FIRM; incr hit; incr nrob; puts "ROB place: [$i getName] at 41.472 25.92" } }; if {$hit != 1} { error "rob_place: u_pc26.u_rob matched $hit instances" }
set hit 0; foreach i [$b getInsts] { if {[[$i getMaster] getName] eq "ot_sram_1r1w_128x256_m1_r2c2" && [string match "*u_pc27?u_rob*" [ot_rob_strip [$i getName]]]} { $i setOrient R0; $i setLocation [expr {round(306.72 * $dbu)}] [expr {round(25.92 * $dbu)}]; $i setPlacementStatus FIRM; incr hit; incr nrob; puts "ROB place: [$i getName] at 306.72 25.92" } }; if {$hit != 1} { error "rob_place: u_pc27.u_rob matched $hit instances" }
set hit 0; foreach i [$b getInsts] { if {[[$i getMaster] getName] eq "ot_sram_1r1w_128x256_m1_r2c2" && [string match "*u_pc28?u_rob*" [ot_rob_strip [$i getName]]]} { $i setOrient R0; $i setLocation [expr {round(572.4 * $dbu)}] [expr {round(25.92 * $dbu)}]; $i setPlacementStatus FIRM; incr hit; incr nrob; puts "ROB place: [$i getName] at 572.4 25.92" } }; if {$hit != 1} { error "rob_place: u_pc28.u_rob matched $hit instances" }
set nm 0; foreach i [$b getInsts] { if {[[$i getMaster] isBlock]} { incr nm } }; if {$nm != 3} { error "rob_place: expected 3 macros, netlist has $nm" }
