# LEP fixed-profile ring input slots:36flops, same pins/clock/cycles.
uplevel #0 {
set hp_fh [open $::env(RESULTS_DIR)/ot_face_flops.txt a]
set hp_n 0
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[0\]\[0\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[0\]\[0\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {376.968*$ff_dbu}] [expr {14.0*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[1\]\[0\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[1\]\[0\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {378.168*$ff_dbu}] [expr {14.0*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[2\]\[0\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[2\]\[0\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {376.968*$ff_dbu}] [expr {15.2*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[3\]\[0\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[3\]\[0\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {378.168*$ff_dbu}] [expr {15.2*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[0\]\[1\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[0\]\[1\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {377.64*$ff_dbu}] [expr {14.0*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[1\]\[1\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[1\]\[1\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {378.84*$ff_dbu}] [expr {14.0*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[2\]\[1\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[2\]\[1\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {377.64*$ff_dbu}] [expr {15.2*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[3\]\[1\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[3\]\[1\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {378.84*$ff_dbu}] [expr {15.2*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[0\]\[2\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[0\]\[2\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {378.36*$ff_dbu}] [expr {14.0*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[1\]\[2\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[1\]\[2\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {379.56*$ff_dbu}] [expr {14.0*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[2\]\[2\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[2\]\[2\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {378.36*$ff_dbu}] [expr {15.2*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[3\]\[2\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[3\]\[2\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {379.56*$ff_dbu}] [expr {15.2*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[0\]\[3\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[0\]\[3\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {379.08*$ff_dbu}] [expr {14.0*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[1\]\[3\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[1\]\[3\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {380.28*$ff_dbu}] [expr {14.0*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[2\]\[3\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[2\]\[3\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {379.08*$ff_dbu}] [expr {15.2*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[3\]\[3\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[3\]\[3\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {380.28*$ff_dbu}] [expr {15.2*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[0\]\[4\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[0\]\[4\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {379.8*$ff_dbu}] [expr {14.0*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[1\]\[4\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[1\]\[4\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {381.0*$ff_dbu}] [expr {14.0*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[2\]\[4\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[2\]\[4\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {379.8*$ff_dbu}] [expr {15.2*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[3\]\[4\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[3\]\[4\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {381.0*$ff_dbu}] [expr {15.2*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[0\]\[5\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[0\]\[5\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {380.472*$ff_dbu}] [expr {14.0*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[1\]\[5\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[1\]\[5\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {381.67199999999997*$ff_dbu}] [expr {14.0*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[2\]\[5\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[2\]\[5\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {380.472*$ff_dbu}] [expr {15.2*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[3\]\[5\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[3\]\[5\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {381.67199999999997*$ff_dbu}] [expr {15.2*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[0\]\[6\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[0\]\[6\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {381.192*$ff_dbu}] [expr {14.0*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[1\]\[6\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[1\]\[6\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {382.392*$ff_dbu}] [expr {14.0*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[2\]\[6\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[2\]\[6\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {381.192*$ff_dbu}] [expr {15.2*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[3\]\[6\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[3\]\[6\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {382.392*$ff_dbu}] [expr {15.2*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[0\]\[7\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[0\]\[7\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {381.912*$ff_dbu}] [expr {14.0*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[1\]\[7\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[1\]\[7\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {383.11199999999997*$ff_dbu}] [expr {14.0*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[2\]\[7\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[2\]\[7\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {381.912*$ff_dbu}] [expr {15.2*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[3\]\[7\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[66\].u_local/data\[3\]\[7\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {383.11199999999997*$ff_dbu}] [expr {15.2*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[69\].u_local/data\[0\]\[1\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[69\].u_local/data\[0\]\[1\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {8.0*$ff_dbu}] [expr {14.0*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[69\].u_local/data\[1\]\[1\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[69\].u_local/data\[1\]\[1\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {9.2*$ff_dbu}] [expr {14.0*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[69\].u_local/data\[2\]\[1\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[69\].u_local/data\[2\]\[1\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {8.0*$ff_dbu}] [expr {15.2*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
set hp_i [$ff_blk findInst {u_land.u_kn.u_w.g_chunk\[69\].u_local/data\[3\]\[1\]$_DFFE_PP_}]
if {$hp_i eq "NULL" || $hp_i eq ""} {error {HEAD_SLOT_FIT missing u_land.u_kn.u_w.g_chunk\[69\].u_local/data\[3\]\[1\]$_DFFE_PP_}}
set hp_got [ff_put_near $hp_i [expr {9.2*$ff_dbu}] [expr {15.2*$ff_dbu}]]
if {$hp_got eq ""} {error {HEAD_SLOT_FIT no legal location}}
puts $hp_fh "[$hp_i getName]\tSLOT\t[expr {[lindex $hp_got 0]/double($ff_dbu)}]\t[expr {[lindex $hp_got 1]/double($ff_dbu)}]\tLEP_SLOT_PIN_FIX"
incr hp_n
close $hp_fh
puts "HEAD_SLOT_FIT moved $hp_n existing ring slots; no new flops/cycles"
}
