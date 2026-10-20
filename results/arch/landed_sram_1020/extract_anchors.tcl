# Read-only extraction from a diagnostic placed checkpoint. Never writes a DB.
read_db $::env(ANCHOR_ODB)
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set out [open $::env(ANCHOR_TSV) {WRONLY CREAT EXCL}]
puts $out "net\tinstance\tmaster\tpin\tdirection\tsignal\tx_um\ty_um\txy_valid"
set count 0
foreach net [$block getNets] {
    set selected 0
    foreach it [$net getITerms] {
        if {[regexp {(^|[./])u_lpl_[0-9]+_[wr]([./]|$)} [[$it getInst] getName]]} {set selected 1; break}
    }
    if {!$selected} {continue}
    foreach it [$net getITerms] {
        set inst [$it getInst]
        lassign [$it getAvgXY] valid x y
        if {$valid} {set x [expr {$x/double($dbu)}]; set y [expr {$y/double($dbu)}]} else {set x ""; set y ""}
        puts $out [join [list [$net getName] [$inst getName] [[$inst getMaster] getName] [[$it getMTerm] getName] [$it getIoType] [$it getSigType] $x $y $valid] "\t"]
        incr count
    }
    foreach bt [$net getBTerms] {
        lassign [$bt getFirstPinLocation] valid x y
        if {$valid} {set x [expr {$x/double($dbu)}]; set y [expr {$y/double($dbu)}]} else {set x ""; set y ""}
        puts $out [join [list [$net getName] TOP PORT [$bt getName] [$bt getIoType] [$bt getSigType] $x $y $valid] "\t"]
    }
}
close $out
puts "ANCHOR_READONLY_EXPORTED $count iterms dbu=$dbu"
exit
