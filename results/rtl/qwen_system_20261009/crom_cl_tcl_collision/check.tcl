array set k {L 0 R 0 B 0 T 0}
if {![catch {set k 0} message] || $message ne {can't set "k": variable is array}} {error "baseline collision missing"}
puts "BASELINE_EXPECTED_FAILURE: $message"
set before [array get k]
set ot_cromcl_band_index 0
set l 17; set ot_win 12.15; set w 0.682; set ot_y0 492.0; set ncol 17; set dy 1.3
for {set expected_index 0} {$expected_index < 100} {incr expected_index} {
 set x [expr {$l*$ot_win+0.25+($ot_cromcl_band_index%$ncol)*$w}]
 set y [expr {$ot_y0+($ot_cromcl_band_index/$ncol)*$dy}]
 if {$x != [expr {$l*$ot_win+0.25+($expected_index%$ncol)*$w}] || $y != [expr {$ot_y0+($expected_index/$ncol)*$dy}]} {error "coordinates changed"}
 incr ot_cromcl_band_index
}
if {[array get k] ne $before} {error "anchor array changed"}
puts "FIX_PASS: 100 coordinate calculations identical; anchor array preserved"
