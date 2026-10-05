# Opt-in post-link/post-floorplan hook for ot_hbm_accel_loader_host_addr_crc.
# ENABLE1 ND1 ADDR37 STACK2 STACK_BYTES22500000000 CRC_MATRIX1.
# No new clock, stage, credit, ACK, macro or parent floorplan.
# Call ot_loader_crc_quadrants with a dict of the four exclusive synthesized
# matrix/input-buffer/hold-mux instance-name lists. Existing CRC FFs are added
# automatically and asserted. Never guess generated gate names from RTL.
set ot_loader_crc_boxes [dict create \
    crc_got_load  {8.64 298.944 273.024 563.328} \
    crc_got_store {298.944 298.944 563.328 563.328} \
    vcrc_load     {8.64 8.64 273.024 273.024} \
    mcrc_store   {298.944 8.64 563.328 273.024}]
proc ot_loader_crc_quadrants {exclusive_cones} {
    global ot_loader_crc_boxes
    set block [ord::get_db_block]
    set units [$block getDbUnitsPerMicron]
    set seen [dict create]
    foreach fold {crc_got_load crc_got_store vcrc_load mcrc_store} {
        if {![dict exists $exclusive_cones $fold] || ![llength [dict get $exclusive_cones $fold]]} {
            error "Missing synthesized exclusive CRC cone: $fold"
        }
        switch $fold {
            crc_got_load  {set engine u_load;  set state crc_got}
            crc_got_store {set engine u_store; set state crc_got}
            vcrc_load     {set engine u_load;  set state vcrc}
            mcrc_store    {set engine u_store; set state mcrc}
        }
        set members [dict get $exclusive_cones $fold]
        set nstate 0
        foreach inst [$block getInsts] {
            set name [string map {\\ ""} [$inst getName]]
            set prefix "g_on.g_die\[0\].${engine}.g_on.${state}\["
            # Original Yosys FF names retained; exclude associated TIE cells.
            if {[string first $prefix $name] == 0 &&
                [string match *DFF* [[$inst getMaster] getName]]} {
                lappend members [$inst getName]
                incr nstate
            }
        }
        if {$nstate != 32} {error "$fold: expected actual 32 retained state FFs, found $nstate"}
        set members [lsort -unique $members]
        foreach name $members {
            if {[dict exists $seen $name]} {error "Cross-fold shared cell requires repricing: $name"}
            dict set seen $name $fold
            if {[$block findInst $name] == "NULL"} {error "CRC placement member missing: $name"}
        }
        set region [odb::dbRegion_create $block "loader.$fold"]
        $region setRegionType FENCE
        set coords {}
        foreach v [dict get $ot_loader_crc_boxes $fold] {lappend coords [expr {round($v*$units)}]}
        odb::dbBox_create $region {*}$coords
        set group [odb::dbGroup_create $block "loader.$fold"]
        $group setRegion $region
        foreach name $members {$group addInst [$block findInst $name]}
    }
}
