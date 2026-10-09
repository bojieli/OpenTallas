# Place the already selected output drivers at the actual IO landing edge.
# +0 cells/cycles. Keep connectivity editable for input-net and hold repair.
set ob [ord::get_db_block]
set ou [[ord::get_db_tech] getDbUnitsPerMicron]
set orow [lindex [$ob getRows] 0]
lassign [$orow getOrigin] ox oy
set op [[$orow getSite] getWidth]
set oh [[$orow getSite] getHeight]
set oc [$ob getCoreArea]
set data_ports {};set other_ports {}
foreach port [$ob getBTerms] {
    if {[$port getIoType] ne "OUTPUT"} {continue}
    set xy [$port getFirstPinLocation]
    if {![lindex $xy 0]} {error "output landing requires placed IO pins"}
    if {[regexp {^captured_data\[[0-9]+\]$} [$port getName]]} {
        lappend data_ports [list [lindex $xy 2] $port]
    } else {lappend other_ports [list [lindex $xy 2] $port]}
}
if {[llength $data_ports]!=256 || [llength $other_ports]!=2} {error "unexpected output landing shape"}
set rank 0;set top_rank 0;set count 0;set used [dict create];set max_distance 0.0
foreach record [concat [lsort -integer -index 0 $data_ports] $other_ports] {
    lassign $record py port
    set xy [$port getFirstPinLocation];set px [lindex $xy 1]
    set drivers {}
    foreach t [[$port getNet] getITerms] {if {[$t getIoType] eq "OUTPUT"} {lappend drivers $t}}
    if {[llength $drivers]!=1} {error "output landing requires one selected driver"}
    set driver [lindex $drivers 0];set cell [$driver getInst];set master [$cell getMaster]
    if {[$master getName] ne "BUFx24_ASAP7_75t_R"} {error "output landing requires selected BUF24"}
    set w [$master getWidth]
    if {[regexp {^captured_data\[} [$port getName]]} {
        set x [expr {$ox+floor(([$oc xMax]-2000-$w-($rank%4)*1728-$ox)/double($op))*$op}]
        set y [expr {$oy+round(($py-$oh/2.0-$oy)/double($oh))*$oh}]
        incr rank
    } else {
        set x [expr {$ox+round(($px-$w/2.0-$ox)/double($op))*$op}]
        set y [expr {$oy+floor(([$oc yMax]-$oh*(1+2*$top_rank)-$oy)/double($oh))*$oh}]
        incr top_rank
    }
    set rows {}
    foreach row [$ob getRows] {
        set rb [$row getBBox]
        if {$y==[$rb yMin] && $x>=[$rb xMin] && $x+$w<=[$rb xMax]} {lappend rows $row}
    }
    if {[llength $rows]!=1} {error "output buffer has no unique containing row"}
    set key "$x,$y"
    if {[dict exists $used $key]} {error "output buffer landing collision"}
    dict for {prior box} $used {
        lassign $box bx by bw
        if {$y==$by && $x<$bx+$bw+2*$op && $x+$w+2*$op>$bx} {
            error "output buffer landing overlap/padding collision"
        }
    }
    dict set used $key [list $x $y $w]
    unset_dont_touch [get_cells [$cell getName]]
    $cell setPlacementStatus PLACED
    place_inst -name [$cell getName] -location [list [expr {$x/double($ou)}] [expr {$y/double($ou)}]] \
        -orientation [[lindex $rows 0] getOrient] -status FIRM
    set dxy [$driver getAvgXY]
    set distance [expr {(abs($px-[lindex $dxy 1])+abs($py-[lindex $dxy 2]))/double($ou)}]
    set max_distance [expr {max($max_distance,$distance)}]
    incr count
}
if {$count!=258 || $max_distance>12.0} {error "output landing count/distance failed"}
puts "MD6_OUTPUT_LANDING count=$count max_actual_Y_to_port_um=$max_distance FIRM=true connectivity_editable=true"
