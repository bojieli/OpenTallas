set htr_occupied {}
proc htr_occupy {args} {global htr_occupied;lappend htr_occupied $args}
proc block {op} {if {$op eq "getBlockages"} {return {hard partial soft}};error $op}
proc hard {op} {switch $op {isSoft {return 0} getMaxDensity {return 0} getBBox {return box}}}
proc soft {op} {switch $op {isSoft {return 1} getMaxDensity {return 0} getBBox {error "soft was treated hard"}}}
proc partial {op} {switch $op {isSoft {return 0} getMaxDensity {return 40} getBBox {error "density was treated hard"}}}
proc box {op} {return 1}
set htr_b block
set f [open [lindex $argv 0]];set src [read $f];close $f
set a [string first {foreach blockage [$htr_b getBlockages]} $src]
set z [string first {foreach inst [$htr_b getInsts]} $src]
eval [string range $src $a [expr {$z-1}]]
if {[llength $htr_occupied]!=1} {error "hard island lost"}
puts "PASS actual relay TCL: hard island retained; partial40% and soft do not forbid FIRM sites"
