# Native OpenDB placement fences. EXCLUSIVE regions and VOLTAGE_DOMAIN groups
# are the group types consumed by native GPL and DPL. No supply nets, rails,
# clock constraints, core edits, or placement coordinates are added here.
proc ot_native_cell_fence {name box inst_names} {
    if {[llength $box] != 4 || [llength $inst_names] == 0} { error "NATIVE_FENCE empty/invalid $name" }
    lassign $box x0 y0 x1 y1
    if {$x1 <= $x0 || $y1 <= $y0} { error "NATIVE_FENCE invalid box $name" }
    set b [ord::get_db_block]
    if {[$b findGroup $name] ne "NULL" || [$b findRegion $name] ne "NULL"} { error "NATIVE_FENCE duplicate $name" }
    set seen [dict create]
    foreach nm $inst_names {
        if {[dict exists $seen $nm]} { error "NATIVE_FENCE duplicate instance $nm" }
        dict set seen $nm 1
        set i [$b findInst $nm]
        if {$i eq "NULL"} { error "NATIVE_FENCE missing instance $nm" }
        if {[[$i getMaster] isBlock]} { error "NATIVE_FENCE macro forbidden $nm" }
        if {[$i getGroup] ne "NULL"} {error "NATIVE_FENCE conflicting existing owner $nm"}
    }
    set u [[ord::get_db_tech] getDbUnitsPerMicron]
    set r [odb::dbRegion_create $b $name]
    $r setRegionType EXCLUSIVE
    odb::dbBox_create $r [expr {round($x0*$u)}] [expr {round($y0*$u)}] [expr {round($x1*$u)}] [expr {round($y1*$u)}]
    set g [odb::dbGroup_create $r $name]
    $g setType VOLTAGE_DOMAIN
    foreach nm $inst_names { $g addInst [$b findInst $nm] }
    puts "NATIVE_FENCE_CREATED name=$name box=$box cells=[llength [$g getInsts]]"
}
proc ot_native_cell_fence_check {name box stage} {
    set b [ord::get_db_block]
    set g [$b findGroup $name]
    if {$g eq "NULL" || [llength [$g getInsts]] == 0} { error "NATIVE_FENCE_CHECK missing/empty $name at $stage" }
    set u [[ord::get_db_tech] getDbUnitsPerMicron]
    lassign $box x0 y0 x1 y1
    foreach i [$g getInsts] {
        set bb [$i getBBox]
        if {[$bb xMin] < round($x0*$u) || [$bb yMin] < round($y0*$u) || [$bb xMax] > round($x1*$u) || [$bb yMax] > round($y1*$u)} {
            error "NATIVE_FENCE_CHECK outside name=$name cell=[$i getName] stage=$stage box=$box"
        }
    }
    puts "NATIVE_FENCE_CHECK_PASS name=$name stage=$stage cells=[llength [$g getInsts]] box=$box"
}

# Explicit ownership is required for multiple regions. Only a SINGLE full-band
# owner may adopt every unowned standard cell; do not use this for HWIN's
# multiple local event/controller regions without its mapped ownership proof.
proc ot_native_cell_fence_add {name inst_names} {
    set b [ord::get_db_block]
    set g [$b findGroup $name]
    if {$g eq "NULL"} {error "NATIVE_FENCE_ADD missing group $name"}
    foreach nm $inst_names {
        set i [$b findInst $nm]
        if {$i eq "NULL" || [[$i getMaster] isBlock]} {error "NATIVE_FENCE_ADD invalid cell $nm"}
        set old [$i getGroup]
        if {$old ne "NULL" && [$old getName] ne $name} {error "NATIVE_FENCE_ADD conflicting owner $nm"}
    }
    foreach nm $inst_names {$g addInst [$b findInst $nm]}
    puts "NATIVE_FENCE_ADDED name=$name cells=[llength $inst_names]"
}
proc ot_native_cell_fence_adopt_unowned {name} {
    set names {}
    foreach i [[ord::get_db_block] getInsts] {
        if {![[$i getMaster] isBlock] && [$i getGroup] eq "NULL"} {lappend names [$i getName]}
    }
    ot_native_cell_fence_add $name $names
    return [llength $names]
}
# A physical band audit covers ALL non-macro instances, including clock/reset/
# hold buffers, fillers and fixed cells born after the initial fence. Vias and
# routed metal are deliberately outside this placement-only check's scope.
proc ot_native_cell_band_check {box stage} {
    lassign $box x0 y0 x1 y1
    set u [[ord::get_db_tech] getDbUnitsPerMicron]
    set n 0
    foreach i [[ord::get_db_block] getInsts] {
        if {[[$i getMaster] isBlock]} {continue}
        incr n
        set bb [$i getBBox]
        if {[$bb xMin] < round($x0*$u) || [$bb yMin] < round($y0*$u) || [$bb xMax] > round($x1*$u) || [$bb yMax] > round($y1*$u)} {
            error "NATIVE_BAND_CHECK outside cell=[$i getName] stage=$stage box=$box"
        }
    }
    puts "NATIVE_BAND_CHECK_PASS stage=$stage cells=$n box=$box"
}

# Native DPL does not guarantee recovery of a birth initially outside its group.
# Seed ONLY explicitly declared new movable cells inside the owner's box before
# DPL. Existing and fixed cells must not be passed here. Timing/reach/PG are
# measured again after legalization; this is not a routing or timing waiver.
proc ot_native_cell_fence_seed_new {name box inst_names} {
    set b [ord::get_db_block]
    set u [[ord::get_db_tech] getDbUnitsPerMicron]
    lassign $box x0 y0 x1 y1
    set max_move 0
    set plans {}
    foreach nm $inst_names {
        set i [$b findInst $nm]
        if {$i eq "NULL" || [[$i getMaster] isBlock]} {error "NATIVE_FENCE_SEED invalid $nm"}
        if {[$i getPlacementStatus] ni {NONE UNPLACED SUGGESTED PLACED}} {error "NATIVE_FENCE_SEED fixed or unsupported cell $nm status=[$i getPlacementStatus]"}
        set g [$i getGroup]
        if {$g eq "NULL" || [$g getName] ne $name} {error "NATIVE_FENCE_SEED wrong owner $nm"}
        set bb [$i getBBox]
        set w [expr {[$bb xMax]-[$bb xMin]}]
        set h [expr {[$bb yMax]-[$bb yMin]}]
        set lo_x [expr {round($x0*$u)}];set lo_y [expr {round($y0*$u)}]
        set hi_x [expr {round($x1*$u)-$w}];set hi_y [expr {round($y1*$u)-$h}]
        if {$hi_x<$lo_x || $hi_y<$lo_y} {error "NATIVE_FENCE_SEED cell does not fit $nm"}
        lassign [$i getLocation] ox oy
        set nx [expr {max($lo_x,min($hi_x,$ox))}]
        set ny [expr {max($lo_y,min($hi_y,$oy))}]
        set max_move [expr {max($max_move,abs($nx-$ox)+abs($ny-$oy))}]
        lappend plans [list $i $nx $ny]
    }
    foreach plan $plans {
        lassign $plan i nx ny
        $i setLocation $nx $ny
        $i setPlacementStatus PLACED
    }
    puts "NATIVE_FENCE_SEED name=$name new_cells=[llength $inst_names] max_move_um=[expr {$max_move/double($u)}]"
}
