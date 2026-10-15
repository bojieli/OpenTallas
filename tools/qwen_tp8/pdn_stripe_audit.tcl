# Read an existing, completed PDN database. No placement or PDN mutation.
if {![info exists ::env(OT_PDN_ODB)] || ![info exists ::env(OT_PDN_AUDIT)]} {
    error "OT_PDN_ODB and OT_PDN_AUDIT are required"
}
read_db $::env(OT_PDN_ODB)
set block [ord::get_db_block]
set u [$block getDbUnitsPerMicron]
set die [$block getDieArea]
set f [open $::env(OT_PDN_AUDIT) w]
puts $f "net,layer,center_um,width_um,x0_um,y0_um,x1_um,y1_um"
foreach net [$block getNets] {
    if {[$net getName] ni {VDD VSS}} {continue}
    foreach sw [$net getSWires] {foreach box [$sw getWires] {
        if {[$box isVia]} {continue}
        set layer [[$box getTechLayer] getName]
        if {$layer ni {M8 M9}} {continue}
        set x0 [$box xMin]; set x1 [$box xMax]
        set y0 [$box yMin]; set y1 [$box yMax]
        if {$layer eq "M8"} {
            if {$x1-$x0 < 0.8*[$die dx]} {continue}
            set center [expr {($y0+$y1)/(2.0*$u)}]
            set width [expr {($y1-$y0)/double($u)}]
        } else {
            if {$y1-$y0 < 0.8*[$die dy]} {continue}
            set center [expr {($x0+$x1)/(2.0*$u)}]
            set width [expr {($x1-$x0)/double($u)}]
        }
        puts $f "[$net getName],$layer,$center,$width,[expr {$x0/double($u)}],[expr {$y0/double($u)}],[expr {$x1/double($u)}],[expr {$y1/double($u)}]"
    }}
}
close $f
puts "PDN_STRIPE_AUDIT $::env(OT_PDN_AUDIT)"
