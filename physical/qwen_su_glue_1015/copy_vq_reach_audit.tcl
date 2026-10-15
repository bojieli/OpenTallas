# Source after read_db of the actual detailed-route final ODB. No HPWL proxy for route length.
set qb [ord::get_db_block]
set qu [$qb getDbUnitsPerMicron]
set qf [open /out/pin_station.csv w]
puts $qf "port,station,pin_x_um,pin_y_um,station_a_x_um,station_a_y_um,manhattan_um"
set qn 0;set qmax 0
foreach bt [$qb getBTerms] {
 if {[$bt getIoType] ne "INPUT" || ![regexp {^vq[0-3]\[[0-9]+\]$} [$bt getName]]} continue
 set nn [$bt getNet];set load {}
 foreach it [$nn getITerms] {if {[$it isInputSignal]} {lappend load $it}}
 if {[llength $load]!=1} {error "COPY_REACH: protected portnet must have one actual receiver"}
 set it [lindex $load 0];set inst [$it getInst]
 if {![string match "ot_qcopy_vq_*" [$inst getName]] || [[$inst getMaster] getName] ne "BUFx4f_ASAP7_75t_R" || [[$it getMTerm] getName] ne "A"} {error "COPY_REACH: station missing/retyped at [$bt getName]"}
 lassign [$it getAvgXY] ok ax ay
 if {!$ok} {error "COPY_REACH: missing real station pin geometry"}
 set found 0
 foreach bp [$bt getBPins] {foreach r [$bp getBoxes] {set px [expr {([$r xMin]+[$r xMax])/2}];set py [expr {([$r yMin]+[$r yMax])/2}];set found 1;break};if {$found} break}
 if {!$found} {error "COPY_REACH: missing real face pin geometry"}
 set d [expr {double(abs($px-$ax)+abs($py-$ay))/$qu}]
 set qmax [expr {max($qmax,$d)}]
 puts $qf "[$bt getName],[$inst getName],[expr {double($px)/$qu}],[expr {double($py)/$qu}],[expr {double($ax)/$qu}],[expr {double($ay)/$qu}],$d"
 incr qn
}
close $qf
if {$qn!=2048 || $qmax>100} {error "COPY_REACH: n=$qn maxpointreach=$qmax um"}
report_wire_length -net {vq*} -detailed_route -file /out/vq_detailed_wirelength.csv
puts "COPY_REACH: actual receiver count=$qn max pin-to-A Manhattan=$qmax um; detailed route lengths separately emitted"
