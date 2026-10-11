# PRE_GLOBAL_PLACE, TILECLK candidate only: actual capture FFs, lockups, and
# output pin FFs own their pin seats. No other cells or paths are moved/exempted.
# ORFS source_step_tcl invokes hooks inside a procedure. Share only helpers
# state explicitly, so helper procs see the same rows/occupancy in either scope.
global mx_rows mx_nr mx_occ
set mx_blk [ord::get_db_block]
set mx_dbu [$mx_blk getDbUnitsPerMicron]
set mx_io /src/physical/hbm_cp_mtp_native/collar_mx1/hfd_cmdproc_s_mtp_native_mx1/io_place.tcl
set f [open $mx_io];set t [read $f];close $f
set mx_pin [dict create]
foreach {m n x y} [regexp -all -inline {place_pin -pin_name \{([^\}]+)\} -layer \S+ -location \{(\S+) (\S+)\}} $t] {
    dict set mx_pin $n [list [expr {round($x*$mx_dbu)}] [expr {round($y*$mx_dbu)}]]
}
set mx_rows {}
foreach r [$mx_blk getRows] {
    set o [$r getOrigin];set site [$r getSite]
    lappend mx_rows [list [lindex $o 1] [lindex $o 0] [expr {[lindex $o 0]+[$r getSiteCount]*[$site getWidth]}] [$site getWidth] [$site getHeight] [$r getOrient]]
}
set mx_rows [lsort -integer -index 0 $mx_rows]
set mx_y0 [lindex $mx_rows 0 0];set mx_rh [lindex $mx_rows 0 4];set mx_sw [lindex $mx_rows 0 3]
set mx_nr [llength $mx_rows]
proc mx_row_at {y} {
    global mx_rows mx_nr
    set lo 0;set hi $mx_nr
    while {$lo<$hi} {
        set mid [expr {($lo+$hi)/2}]
        if {[lindex $mx_rows $mid 0]<$y} {set lo [expr {$mid+1}]} else {set hi $mid}
    }
    return [expr {min($mx_nr-1,$lo)}]
}
array set mx_occ {}
foreach i [$mx_blk getInsts] {
    if {![$i isFixed]} continue
    set b [$i getBBox]
    for {set ri [mx_row_at [$b yMin]]} {$ri<$mx_nr && [lindex $mx_rows $ri 0]<[$b yMax]} {incr ri} {
        lappend mx_occ($ri) [list [$b xMin] [$b xMax]]
    }
}
proc mx_free {ri x0 x1} {
    global mx_occ
    if {![info exists mx_occ($ri)]} {return 1}
    foreach iv $mx_occ($ri) {if {$x0<[lindex $iv 1] && [lindex $iv 0]<$x1} {return 0}}
    return 1
}
set mx_n 0;set mx_max 0;set mx_report [open /work/mx1_pin_stations.tsv w]
puts $mx_report "instance\tport\trole\tport_distance_um\tcell_x_um\tcell_y_um"
foreach i [$mx_blk getInsts] {
    if {![[$i getMaster] isSequential]} continue
    set n [string map {"\\" ""} [$i getName]];set pn "";set role ""
    if {[regexp {^ar\.i0_(cSE|cSW|f_loader|f_router|xb)\[([0-9]+)\]} $n -> p k]} {set pn "$p\[$k\]";set role input}
    if {[regexp {^ar\.lk_(cSE|cSW|f_loader|f_router|xb)\[([0-9]+)\]} $n -> p k]} {set pn "$p\[$k\]";set role input_lockup}
    if {[regexp {^ar\.g_o_(cSE|cSW|t_su_SE|t_su_SW|xl|xt)_[0-9]+\[([0-9]+)\]\.u[/\.]q} $n -> p k]} {set pn "$p\[$k\]";set role output}
    if {[regexp {^ar\.u_o_(cSE|cSW)_([0-9]+)[/\.]q} $n -> p k]} {set pn "$p\[$k\]";set role output}
    if {[regexp {^ar\.g_o_(cSE|cSW|t_su_SE|t_su_SW|xl|xt)_[0-9]+\[([0-9]+)\]\.u[/\.]lk} $n -> p k]} {set pn "$p\[$k\]";set role output_lockup}
    if {[regexp {^ar\.u_o_(cSE|cSW)_([0-9]+)[/\.]lk} $n -> p k]} {set pn "$p\[$k\]";set role output_lockup}
    if {[regexp {^ar\.i1_(cSE|cSW|f_loader)\[([0-9]+)\]} $n -> p k]} {set pn "$p\[$k\]";set role core_crossing_capture}
    if {[regexp {^ar\.i_(f_router|xb)\[([0-9]+)\]} $n -> p k]} {set pn "$p\[$k\]";set role core_crossing_capture}
    # host job channel pin flops (mtp-mx1 2026-10-10): hv_q <- f_host[0], hd_q[k] <- f_host[k+1]
    if {[regexp {^g_regb\.hv_q} $n]} {set pn "f_host\[0\]";set role input}
    if {[regexp {^g_regb\.hd_q\[([0-9]+)\]} $n -> k]} {set pn "f_host\[[expr {$k+1}]\]";set role input}
    # MTP-native pin flops (mtp-mx1 2026-10-10, FT13): receivers, transmitters, registered outputs, level pin flops and
    # the die-reset synchroniser sit at their own pins (design standard: pin flops anchored at their pins)
    if {[regexp {^g_regb\.u_rx_ef[./]d_q\[([0-9]+)\]} $n -> k]} {set pn "f_mtp\[[expr {$k+44}]\]";set role mtp_pin}
    if {[regexp {^g_regb\.u_rx_ef[./]v_q(\$|$)} $n]} {set pn "f_mtp\[43\]";set role mtp_pin}
    if {[regexp {^g_regb\.u_rx_ef[./]in_ready(\$|$)} $n]} {set pn "t_mtp\[139\]";set role mtp_pin}
    if {[regexp {^g_regb\.u_rx_cf[./]d_q\[([0-9]+)\]} $n -> k]} {set pn "f_mtp\[[expr {$k+83}]\]";set role mtp_pin}
    if {[regexp {^g_regb\.u_rx_cf[./]v_q(\$|$)} $n]} {set pn "f_mtp\[82\]";set role mtp_pin}
    if {[regexp {^g_regb\.u_rx_cf[./]in_ready(\$|$)} $n]} {set pn "t_mtp\[82\]";set role mtp_pin}
    if {[regexp {^g_regb\.u_rx_kf[./]d_q\[([0-9]+)\]} $n -> k]} {set pn "f_backend\[[expr {$k+2}]\]";set role mtp_pin}
    if {[regexp {^g_regb\.u_rx_kf[./]v_q(\$|$)} $n]} {set pn "f_backend\[1\]";set role mtp_pin}
    if {[regexp {^g_regb\.u_rx_kf[./]in_ready(\$|$)} $n]} {set pn "t_backend\[270\]";set role mtp_pin}
    if {[regexp {^g_regb\.u_tx_bf[./]out_data\[([0-9]+)\]} $n -> k]} {set pn "t_backend\[[expr {$k+1}]\]";set role mtp_pin}
    if {[regexp {^g_regb\.u_tx_bf[./]out_valid(\$|$)} $n]} {set pn "t_backend\[0\]";set role mtp_pin}
    if {[regexp {^g_regb\.u_tx_hf[./]out_data\[([0-9]+)\]} $n -> k]} {set pn "t_emit_host\[[expr {$k+1}]\]";set role mtp_pin}
    if {[regexp {^g_regb\.u_tx_hf[./]out_valid(\$|$)} $n]} {set pn "t_emit_host\[0\]";set role mtp_pin}
    if {[regexp {^g_regb\.u_tx_df[./]out_valid(\$|$)} $n]} {set pn "t_emit_host\[74\]";set role mtp_pin}
    if {[regexp {^g_regb\.tm_q\[([0-9]+)\]} $n -> k]} {set pn "t_mtp\[[expr {$k+0}]\]";set role mtp_pin}
    if {[regexp {^g_regb\.th_q\[([0-9]+)\]} $n -> k]} {set pn "t_host\[[expr {$k+0}]\]";set role mtp_pin}
    if {[regexp {^g_regb\.te_q\[([0-9]+)\]} $n -> k]} {set pn "t_emit\[[expr {$k+0}]\]";set role mtp_pin}
    if {[regexp {^g_regb\.tp_q\[([0-9]+)\]} $n -> k]} {set pn "t_provider\[[expr {$k+0}]\]";set role mtp_pin}
    if {[regexp {^g_regb\.teh_q\[([0-9]+)\]} $n -> k]} {set pn "t_emit_host\[[expr {$k+75}]\]";set role mtp_pin}
    if {[regexp {^g_regb\.ab_q(\$|$)} $n]} {set pn "t_abort\[0\]";set role mtp_pin}
    if {[regexp {^g_regb\.dr_q(\$|$)} $n]} {set pn "t_drained\[0\]";set role mtp_pin}
    if {[regexp {^g_regb\.q81(\$|$)} $n]} {set pn "f_mtp\[81\]";set role mtp_pin}
    if {[regexp {^g_regb\.q71(\$|$)} $n]} {set pn "f_backend\[71\]";set role mtp_pin}
    if {[regexp {^g_regb\.q72(\$|$)} $n]} {set pn "f_backend\[72\]";set role mtp_pin}
    if {[regexp {^g_regb\.qam(\$|$)} $n]} {set pn "f_am\[0\]";set role mtp_pin}
    if {[regexp {^g_regb\.qst\[([0-9]+)\]} $n -> k]} {set pn "f_mtp\[[expr {$k+514}]\]";set role mtp_pin}
    if {[regexp {^g_regb\.qami\[([0-9]+)\]} $n -> k]} {set pn "f_am\[[expr {$k+1}]\]";set role mtp_pin}
    if {[regexp {^g_regb\.qid\[([0-9]+)\]} $n -> k]} {set pn "f_backend\[[expr {$k+2}]\]";set role mtp_pin}
    if {[regexp {^g_regb\.rs\[[01]\]} $n]} {set pn "rst\[0\]";set role mtp_pin}
    if {$pn eq ""} continue
    if {![dict exists $mx_pin $pn]} {error "MX1 pin station $n has no actual pin $pn"}
    lassign [dict get $mx_pin $pn] px py
    set w [[$i getMaster] getWidth];set wr [expr {$w+3*$mx_sw}]
    set r0 [mx_row_at $py]
    set placed 0
    for {set dr 0} {$dr<80 && !$placed} {incr dr} {
        set ri [expr {$r0+(($dr%2)?-(($dr+1)/2):($dr/2))}]
        if {$ri<0 || $ri>=$mx_nr} continue
        lassign [lindex $mx_rows $ri] ry rx0 rx1 site rh orient
        # Inner six-micrometre seat; spread occupied sites deeper within24um.
        set tx [expr {max($rx0+6*$mx_dbu,min($rx1-$wr-6*$mx_dbu,$px))}]
        for {set dx 0} {$dx<12 && !$placed} {incr dx} {
            set sign [expr {$px>($rx0+$rx1)/2?-1:1}]
            set x [expr {$rx0+int(($tx+$sign*$dx*($wr+3*$site)-$rx0)/$site)*$site}]
            if {$x<$rx0 || $x+$wr>$rx1 || ![mx_free $ri $x [expr {$x+$wr}]]} continue
            set dist [expr {(abs($x-$px)+abs($ry-$py))/double($mx_dbu)}]
            if {$dist>24.0} continue
            $i setOrient $orient;$i setLocation $x $ry;$i setPlacementStatus FIRM
            lappend mx_occ($ri) [list $x [expr {$x+$wr}]]
            puts $mx_report [join [list $n $pn $role $dist [expr {$x/double($mx_dbu)}] [expr {$ry/double($mx_dbu)}]] "\t"]
            set mx_max [expr {max($mx_max,$dist)}];incr mx_n;set placed 1
        }
    }
    if {!$placed} { if {[string match g_regb.* $n]} { puts "MX1_PIN_STATIONS WARN no seat within 24um for $n ($pn): left to the placer" } else { error "MX1 no legal pin station for $n within24um of $pn" } }
}
close $mx_report
if {$mx_n==0} {error "MX1 mapped pin station census empty"}
puts "MX1_PIN_STATIONS: $mx_n actual pin FFs/lockups anchored; max Manhattan pin distance $mx_max um"
