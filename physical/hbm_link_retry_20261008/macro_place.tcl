# Full-port pathfinding: four banks, each four protected-record macros.
# Generous channels at55% reservation; no enclosing die allocation claim.
set n 0
foreach inst [[ord::get_db_block] getInsts] {
 if {[[$inst getMaster] getName] ne "ot_sram_1r1w_128x256_m1_r2c2"} {continue}
 set nm [string map [list {\[} {[} {\]} {]}] [$inst getName]]
 if {![regexp {g_bank\[([0-9]+)\].*g_macro\[([0-9]+)\].*u_mem} $nm -> b m]} {error "unexpected replay macro $nm"}
 place_macro -macro_name [$inst getName] -location [list [expr {12.0+112.0*$m}] [expr {12.0+75.0*$b}]] -orientation R0
 incr n
}
if {$n!=16} {error "expected16 real replaySRAM macros, placed$n"}
