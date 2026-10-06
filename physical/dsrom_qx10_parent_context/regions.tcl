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
    fq {^u_qx\.u_e\.(g_qo\.g_qyf\.fq|fault)(\[|\$)}
} {
    set fault_count 0
    foreach inst [$block getInsts] {
        set name [string map {\\ {}} [$inst getName]]
        if {[regexp $expression $name] && [string match DFF* [[$inst getMaster] getName]]} {incr fault_count}
    }
    if {$family eq "fq" && $fault_count!=1} {error "QX10 requires one actual fq output register"}
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

# Slang aliases the source fq register to its engine output port, fault.
# Accept that exact alias only after proving the mapped OR-of-three producers.
# QN outputs through AND3 + INV implement ffq | bkf0 | bkf1, not TIEHI/LO.
proc qx10_unique_driver {net} {
    if {$net eq "NULL"} {error "fault semantic gate found an unconnected net"}
    set drivers {}
    foreach terminal [$net getITerms] {
        if {[$terminal getIoType] eq "OUTPUT"} {lappend drivers $terminal}
    }
    if {[llength $drivers]!=1} {error "fault semantic gate requires one actual driver"}
    return [lindex $drivers 0]
}
set aliases {}
foreach inst [$block getInsts] {
    set name [string map {\\ {}} [$inst getName]]
    if {[regexp {^u_qx\.u_e\.fault\$} $name] &&
        [string match DFF* [[$inst getMaster] getName]]} {lappend aliases $inst}
}
if {[llength $aliases]} {
    if {[llength $aliases]!=1} {error "engine fault register alias is not unique"}
    set fq_reg [lindex $aliases 0]
    set inv_pin [qx10_unique_driver [[$fq_reg findITerm D] getNet]]
    set inv [$inv_pin getInst]
    if {[[$inv getMaster] getName] ne "INVx1_ASAP7_75t_R" ||
        [[$inv_pin getMTerm] getName] ne "Y"} {error "fault fq D is not the actual OR output"}
    set and_pin [qx10_unique_driver [[$inv findITerm A] getNet]]
    set and_cell [$and_pin getInst]
    if {[[$and_cell getMaster] getName] ne "AND3x1_ASAP7_75t_R" ||
        [[$and_pin getMTerm] getName] ne "Y"} {error "fault fq OR lost its three producers"}
    set producers {}
    foreach input {A B C} {
        set producer_pin [qx10_unique_driver [[$and_cell findITerm $input] getNet]]
        set producer [$producer_pin getInst]
        if {![string match DFF* [[$producer getMaster] getName]] ||
            [[$producer_pin getMTerm] getName] ne "QN"} {error "fault producer is not a real QN register"}
        if {[[$producer findITerm CLK] getNet] ne [[$fq_reg findITerm CLK] getNet]} {error "fault producer lost its real root-clock relation"}
        lappend producers [string map {\\ {}} [$producer getName]]
    }
    set expected [list {u_qx.u_e.g_qo.g_qyf.ffq$_DFF_PN0_} \
        {u_qx.u_e.g_mac[0].g_qyb.bkf_r$_DFF_PN0_} \
        {u_qx.u_e.g_mac[1].g_qyb.bkf_r$_DFF_PN0_}]
    if {[lsort $producers] ne [lsort $expected]} {error "fault fq no longer captures ffq and both actual bank faults"}
    puts "OT_QX10_FAULT_FQ_ALIAS register=[$fq_reg getName] actual_OR_producers=$producers"
}
rename qx10_unique_driver {}
