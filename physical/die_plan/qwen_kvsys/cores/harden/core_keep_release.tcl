uplevel #0 {
if {![info exists ot_core_kept]} { error "OT_CORE_KEEP: missing PRE_SYNTH_TCL state" }
set n 0
foreach name $ot_core_kept {
    set i [[ord::get_db_block] findInst $name]
    if {$i eq "NULL"} { error "OT_CORE_KEEP: protected register disappeared: $name" }
    $i setDoNotTouch 0
    incr n
}
puts "OT_CORE_KEEP released $n sequential cells (prior dont_touch flags preserved)"
unset ot_core_kept
}
