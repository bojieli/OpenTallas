# Opt-in physical-only repair of the three source-matched Z18d hold sinks.
# Model: three positive BUFx2 cells, 0.2187 um2, three local tracks, zero cycles.
# Run after detail placement, before CTS; final loaded SS60/FF25 is mandatory.
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set icg [$block findInst u_qx.u_e.g_cg.u_cg.u_icg]
if {$icg eq "NULL"} {error "boundary hold requires actual full-engine ICG"}
set gated [[$icg findITerm GCLK] getNet]
set engine_group "NULL"
foreach group [$block getGroups] {
    if {[$group getName] eq "qx10_engine"} {set engine_group $group}
}
if {$engine_group eq "NULL"} {error "actual engine fence missing"}
set ordinal 0
foreach target {
    {u_qx.u_e.g_mac[0].g_mz.u_x/q[450]$_DFF_P_}
    {u_qx.u_e.i2x_q0[133]$_DFF_P_}
    {u_qx.u_e.fw_q0[199]$_DFF_P_}
} {
    set matches {}
    foreach inst [$block getInsts] {
        if {[string map {\\ {}} [$inst getName]] eq $target} {lappend matches $inst}
    }
    if {[llength $matches]!=1} {error "actual hold sink not unique: $target"}
    set sink [lindex $matches 0]
    if {![string match DFF* [[$sink getMaster] getName]]} {error "hold sink is not a real register"}
    set d [$sink findITerm D]
    set clock [$sink findITerm CLK]
    if {$d eq "NULL" || $clock eq "NULL" || [$clock getNet] ne $gated} {
        error "hold sink lacks its literal gated-clock relation: $target"
    }
    set original [$d getNet]
    if {$original eq "NULL"} {error "hold sink data input missing"}
    set name [$sink getName]
    regsub -all {[][\\.^$*+?(){}|]} $name {\\&} expression
    set cells [get_cells -quiet -regexp "^$expression\$"]
    if {[llength $cells]!=1} {error "hold sink STA/ODB identity mismatch"}
    set pins {}
    foreach pin [get_pins -quiet -of_objects $cells] {
        if {[string match */D [get_full_name $pin]]} {lappend pins $pin}
    }
    if {[llength $pins]!=1} {error "actual hold data pin missing in STA"}
    lassign [$sink getLocation] x y
    set buffer_name qx10_boundary_hold_$ordinal
    if {[$block findInst $buffer_name] ne "NULL"} {error "hold hook already applied; no replay"}
    insert_buffer -buffer_cell BUFx2_ASAP7_75t_R -load_pins $pins \
        -buffer_name $buffer_name -net_name qx10_boundary_hold_net_$ordinal \
        -location [list [expr {double($x)/$dbu}] [expr {double($y)/$dbu}]]
    set buffer [$block findInst $buffer_name]
    if {$buffer eq "NULL" || [[$buffer getMaster] getName] ne "BUFx2_ASAP7_75t_R"} {
        error "positive hold buffer not inserted"
    }
    if {[[$buffer findITerm A] getNet] ne $original ||
        [[$buffer findITerm Y] getNet] ne [$d getNet] || [$d getNet] eq $original} {
        error "hold buffer changed data connectivity"
    }
    $engine_group addInst $buffer
    set_dont_touch $buffer_name
    puts "OT_QX10_HOLD_BUFFER sink=$target cell=$buffer_name original_net=[$original getName] new_net=[[$d getNet] getName] actual_gated_net=[$gated getName] added_cycles=0"
    incr ordinal
}
if {$ordinal!=3} {error "all three mandatory hold classes must be covered"}
detailed_placement -incremental
check_placement -verbose
