# el1011-q-sp 2026-10-11: fixed macro placement for the VM bank-group tile ot_qfd_vm_grp (NBK 8, NSU 3, NSB 2, USE_MACRO 1):
# 16 x ot_sram_1r1w_256x256 (172.8 x 41.04; copy-0 banks g_b[0..7], lo / hi side by side in columns 0 / 1, bank g in row g)
# + 12 x ot_sram_1r1w_1024x256 (174.744 x 70.47; SU copies g_c[c].g_s[j], row 2c + j, lo / hi in columns 2 / 3).
# Four macro columns off the W face with 21.6-um channels; the E strip (x >= W - 165) holds the pin flops, x FIFO and
# capture registers next to the E-face pins.  Rows spread over the core height (small: ~27 um, big: ~19 um channels).
set b [ord::get_db_block]
set die [$b getDieArea]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set H [expr {double([$die yMax]) / $dbu}]
set e 21.6
set colx [list $e [expr {$e + 174.744 + $e}] [expr {$e + 2 * (174.744 + $e)}] [expr {$e + 3 * (174.744 + $e)}]]
set gs [expr {($H - 2 * $e - 8 * 41.04) / 7.0}]
set gb [expr {($H - 2 * $e - 6 * 70.47) / 5.0}]
proc ot_snx {v} { return [expr {floor($v / 0.216) * 0.216}] }
proc ot_sny {v} { return [expr {floor($v / 0.27) * 0.27}] }
foreach inst [$b getInsts] {
    set m [[$inst getMaster] getName]
    set n [$inst getName]
    set nn [string map {\\ {}} $n]          ;# getName returns escaped brackets (g_b\[0\]...): parse the plain form
    set hi [string match {*u_hi} $nn]
    if {[string match ot_sram_1r1w_256x256* $m]} {
        if {![regexp {g_b\[(\d+)\]} $nn -> r]} { error "vm_grp_place: unparsed $n" }
        set x [lindex $colx $hi]
        set y [expr {$e + $r * (41.04 + $gs)}]
    } elseif {[string match ot_sram_1r1w_1024x256* $m]} {
        if {![regexp {g_c\[(\d+)\]\.g_s\[(\d+)\]} $nn -> c j]} { error "vm_grp_place: unparsed $n" }
        set x [lindex $colx [expr {2 + $hi}]]
        set y [expr {$e + (2 * $c + $j) * (70.47 + $gb)}]
    } else { continue }
    place_macro -macro_name $n -location [list [ot_snx $x] [ot_sny $y]] -orientation R0
}
