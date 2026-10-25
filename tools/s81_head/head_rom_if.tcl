# Planned macro-side address/CE launch and per-bit ROM capture flops.
# Runs after face_flops.tcl; keeps each original data edge (zero extra cycles).
set hif_f [open $::env(RESULTS_DIR)/ot_face_flops.txt a]
set hif_n 0; set hif_missing {}
foreach i [$ff_blk getInsts] {
    if {![regexp {DFF} [[$i getMaster] getName]]} continue
    set nm [string map [list "\\" ""] [$i getName]]
    set bank "";set pn ""
    if {[regexp {^u_m[./]u_rom_addr([01])[./](?:q|addr)\[([0-9]+)\]} $nm -> bank bit]} {
        set pn "addr_in\[$bit\]"
    } elseif {[regexp {^u_m[./]cap([01])\[([0-9]+)\]} $nm -> bank bit]} {
        set pn "rd_out\[$bit\]"
    } elseif {[regexp {^u_m[./]ce([01])_q} $nm -> bank]} {
        set pn ce_in
    } else {continue}
    set mac [$ff_blk findInst "u_m.u_rom$bank"]
    if {$mac eq "NULL"} {error "head IF: ROM bank$bank absent"}
    set it [$mac findITerm $pn]
    if {$it eq "NULL"} {error "head IF: ROM pin$pn absent"}
    set pb [$it getBBox];set mb [$mac getBBox]
    set px [expr {([$pb xMin]+[$pb xMax])/2.0/$ff_dbu}]
    set py [expr {([$pb yMin]+[$pb yMax])/2.0/$ff_dbu}]
    set mx0 [expr {[$mb xMin]/double($ff_dbu)}];set mx1 [expr {[$mb xMax]/double($ff_dbu)}]
    set my0 [expr {[$mb yMin]/double($ff_dbu)}];set my1 [expr {[$mb yMax]/double($ff_dbu)}]
    set fw [expr {[[$i getMaster] getWidth]/double($ff_dbu)}]
    set fh [expr {[[$i getMaster] getHeight]/double($ff_dbu)}]
    set dl [expr {abs($px-$mx0)}];set dr [expr {abs($px-$mx1)}]
    set db [expr {abs($py-$my0)}];set dt [expr {abs($py-$my1)}]
    set dm [expr {min($dl,$dr,$db,$dt)}]
    set x [expr {$px-$fw/2.0}];set y [expr {$py-$fh/2.0}]
    if {$dm==$dl} {set x [expr {$mx0-5.4-$fw}]
    } elseif {$dm==$dr} {set x [expr {$mx1+5.4}]
    } elseif {$dm==$db} {set y [expr {$my0-5.4-$fh}]
    } else {set y [expr {$my1+5.4}]}
    set got [ff_put_near $i [expr {round($x*$ff_dbu)}] [expr {round($y*$ff_dbu)}]]
    if {$got eq ""} {lappend hif_missing $nm;continue}
    puts $hif_f "[$i getName]\trom_if:$bank:$pn\t[expr {[lindex $got 0]/double($ff_dbu)}]\t[expr {[lindex $got 1]/double($ff_dbu)}]\t-"
    incr hif_n
}
close $hif_f
puts "HEAD_ROM_IF anchored $hif_n missing [llength $hif_missing] $hif_missing"
if {$hif_n<538 || [llength $hif_missing]} {error "HEAD_ROM_IF missing address/capture/CE flops"}
