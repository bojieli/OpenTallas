# Source-sized parent and unchanged full Z18 frame, no density rescue.
set block [ord::get_db_block]
set scale [$block getDbUnitsPerMicron]
foreach {role coords} {
    parent {2.16 2.16 525.096 237.60}
    engine {527.256 44.55 1038.096 195.21}
} {
    set region [odb::dbRegion_create $block qx10_$role]
    $region setRegionType EXCLUSIVE
    set box {};foreach x $coords {lappend box [expr {round($x*$scale)}]}
    odb::dbBox_create $region {*}$box
    set group($role) [odb::dbGroup_create $block qx10_$role]
    $region addGroup $group($role)
    set area($role) 0.;set count($role) 0
}
set macros 0
# ABC's anonymous combinational cells retain connectivity, not hierarchy names.
# Assign the combinational fan-in of actual engine registers/ROMs to the engine,
# stopping at parent registers, explicitly named parent cells and clock nets.
set engine_insts [dict create]
set pending {}
foreach inst [$block getInsts] {
    if {[string match u_qx.* [$inst getName]]} {
        dict set engine_insts [$inst getId] 1
        lappend pending $inst
    }
}
for {set head 0} {$head < [llength $pending]} {incr head} {
    set inst [lindex $pending $head]
    foreach sink [$inst getITerms] {
        if {[$sink getIoType] ne "INPUT"} {continue}
        set net [$sink getNet]
        if {$net eq "NULL" || [$net getSigType] eq "CLOCK" || [$net getName] eq "clk"} {continue}
        foreach driver [$net getITerms] {
            if {[$driver getIoType] ne "OUTPUT"} {continue}
            set upstream [$driver getInst]
            if {[dict exists $engine_insts [$upstream getId]]} {continue}
            set name [$upstream getName]
            set master [$upstream getMaster]
            if {![string match _* $name] || [string match DFF* [$master getName]] || [$master isBlock]} {continue}
            dict set engine_insts [$upstream getId] 1
            lappend pending $upstream
        }
    }
}
foreach inst [$block getInsts] {
    set master [$inst getMaster]
    if {[regexp {SPACER|WELLTAP} [$master getType]]} {continue}
    set role parent
    if {[dict exists $engine_insts [$inst getId]]} {set role engine}
    if {[$master isBlock]} {
        if {$role ne "engine" || [$master getName] ne "ot_rom_4096x274_m8"} {
            error "unexpected macro outside the full QX10 engine"
        }
        incr macros
        continue
    }
    $group($role) addInst $inst
    set area($role) [expr {$area($role)+double([$master getWidth])*[$master getHeight]/$scale/$scale}]
    incr count($role)
}
if {$macros!=4} {error "joined source lost actual FOUR weight ROMs"}
if {$area(parent)>61560.02592 || $area(engine)>27262.61712} {
    error "joined mapped logic exceeds its unchanged analytical parent/engine allocations"
}
puts "OT_QX10_NATIVE_REGIONS parent_cells=$count(parent) parent_area=$area(parent) engine_cells=$count(engine) engine_area=$area(engine) macros=$macros"
# Reject the actual protective-producer disappearance before placement/CTS.
foreach {family expression} {
    ff_d {u_qx\.u_e\.g_qo\.ff_d\[}
    ffq {u_qx\.u_e\.g_qo\.g_qyf\.ffq(\[|\$)}
    fq {u_qx\.u_e\.g_qo\.g_qyf\.fq(\[|\$)}
} {
    set fault_count 0
    foreach inst [$block getInsts] {
        set name [string map {\\ {}} [$inst getName]]
        if {[regexp $expression $name] && [string match DFF* [[$inst getMaster] getName]]} {incr fault_count}
    }
    if {!$fault_count} {error "QX10 fault producer absent after mapping: $family; no constant fault waiver"}
}
foreach bank {0 1} {
    set found 0
    foreach inst [$block getInsts] {
        set name [string map {\\ {}} [$inst getName]]
        if {[string first "u_qx.u_e.g_mac\[$bank\].g_qyb.bkf_r" $name]>=0 &&
            [string match DFF* [[$inst getMaster] getName]]} {incr found}
    }
    if {!$found} {error "QX10 bank${bank} actual protective bkf_r producer absent"}
}
