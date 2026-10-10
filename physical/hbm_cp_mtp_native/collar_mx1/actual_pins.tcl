# Record real ODB terminal rectangles after detail route; no geometry changes.
set mx_b [ord::get_db_block]
set mx_u [$mx_b getDbUnitsPerMicron]
set mx_f [open /work/mx1_actual_pins.tsv w]
puts $mx_f "name\tlayer\tx0_um\ty0_um\tx1_um\ty1_um"
set mx_n 0
foreach t [$mx_b getBTerms] {
    if {[$t getSigType] in {POWER GROUND}} continue
    foreach p [$t getBPins] {
        foreach r [$p getBoxes] {
            puts $mx_f "[$t getName]\t[[$r getTechLayer] getName]\t[expr {[$r xMin]/double($mx_u)}]\t[expr {[$r yMin]/double($mx_u)}]\t[expr {[$r xMax]/double($mx_u)}]\t[expr {[$r yMax]/double($mx_u)}]"
            incr mx_n
        }
    }
}
close $mx_f
puts "MX1_ACTUAL_PIN_RECORD $mx_n rectangles"
