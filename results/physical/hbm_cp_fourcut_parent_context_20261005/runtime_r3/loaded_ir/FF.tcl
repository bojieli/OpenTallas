set ::so_libs {{/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz} {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz} {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz} {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz} {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib} {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_DFFHQNH2V2X_RVT_FF_nldm_FAKE.lib} {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_DFFHQNV2X_RVT_FF_nldm_FAKE.lib}}
set ::so_odb /cp_results/6_final.odb
set ::so_sdc /cp_results/6_final.sdc
set ::so_spef {/cp_results/6_final.spef}
set ::so_platform /OpenROAD-flow-scripts/flow/platforms/asap7
set ::so_pdn_tcl {}
set ::so_saif {}
set ::so_saif_scope {}
set ::so_groups {}
set ::so_inst_power {}
set ::so_derate 0
set ::so_vdd 0.77
set ::so_bump_pitch 140
set ::so_bump_size 50
set ::so_out /cp_output/FF
file mkdir /cp_output/FF

proc emit {key value} { puts "SIGNOFF $key=$value" }
proc sum_list {l} { set s 0.0; foreach x $l { set s [expr {$s + $x}] }; return $s }


read_db $::so_odb
if {$::so_pdn_tcl ne ""} {
    # a PDN variant: rip the route's grid up and build the variant's (before any
    # Liberty is read: pdngen then sees only the LEF masters)
    pdngen -ripup
    source $::so_pdn_tcl
    pdngen
}
foreach lib $::so_libs { read_liberty $lib }
read_sdc $::so_sdc
if {$::so_spef ne ""} {
    read_spef $::so_spef
} else {
    # pre-route stage (e.g. 4_cts.odb): placement-estimated wire parasitics
    source $::so_platform/setRC.tcl
    estimate_parasitics -placement
}
set_clock_latency 0 [all_clocks]
set_propagated_clock [all_clocks]
set_cmd_units -time ns -power W

emit corner.name FF


# -- activity ---------------------------------------------------------------
if {$::so_saif ne ""} {
    read_saif -scope $::so_saif_scope $::so_saif
}
report_activity_annotation
# -- design totals by OpenSTA group ------------------------------------------
# sta::design_power: {total sequential combinational clock macro pad} x
# {internal switching leakage total}, watts
set dp [sta::design_power [sta::cmd_scene]]
set k 0
foreach grp {total sequential combinational clock macro pad} {
    foreach part {internal switching leakage total} {
        emit power.$grp.${part}_w [lindex $dp $k]
        incr k
    }
}
# -- per hierarchy prefix (flat netlist: instance names keep the RTL path) ----
set prefixes $::so_groups
foreach p $prefixes { set gp($p) {0.0 0.0 0.0 0.0 0} }
set gp(__other__) {0.0 0.0 0.0 0.0 0}
set fh ""
if {$::so_inst_power ne ""} { set fh [open $::so_inst_power w] }
foreach inst [get_cells *] {
    set name [get_full_name $inst]
    set ip [sta::instance_power $inst [sta::cmd_scene]]
    set key __other__
    foreach p $prefixes { if {[string first $p $name] == 0} { set key $p; break } }
    lassign $gp($key) a b c d n
    set gp($key) [list [expr {$a + [lindex $ip 0]}] [expr {$b + [lindex $ip 1]}] \
                     [expr {$c + [lindex $ip 2]}] [expr {$d + [lindex $ip 3]}] [expr {$n + 1}]]
    if {$fh ne ""} { puts $fh "$name [lindex $ip 3]" }
}
if {$fh ne ""} { close $fh }
foreach key [array names gp] {
    lassign $gp($key) a b c d n
    emit hier.$key.internal_w $a
    emit hier.$key.switching_w $b
    emit hier.$key.leakage_w $c
    emit hier.$key.total_w $d
    emit hier.$key.instances $n
}

set ::so_source PINS
puts "IRSOURCE PINS"

# -- static IR drop (PSM) with the activity-annotated instance power ---------
# PINS : the block's own M6 PDN pins are ideal sources (block-level sign-off:
#        the parent grid is assumed ideal at the block boundary).
# BUMPS: an explicit flip-chip bump array written as a PSM source file
#        (x,y,size,voltage per line): VDD and VSS bumps alternate in a
#        checkerboard of pitch so_bump_pitch um and land on the block's top
#        PDN layer, i.e. no upper redistribution grid (a pessimistic bound).
set_pdnsim_net_voltage -net VDD -voltage $::so_vdd
set_pdnsim_net_voltage -net VSS -voltage 0.0
set die [[ord::get_db_block] getDieArea]
set dbu [[ord::get_db_block] getDbUnitsPerMicron]
set dx0 [expr {[$die xMin] / double($dbu)}]
set dy0 [expr {[$die yMin] / double($dbu)}]
set dx1 [expr {[$die xMax] / double($dbu)}]
set dy1 [expr {[$die yMax] / double($dbu)}]
emit ir.die_um "[expr {$dx1 - $dx0}]x[expr {$dy1 - $dy0}]"
foreach net {VDD VSS} {
    set vf [file join $::so_out ir_PINS_${net}.csv]
    set ef [file join $::so_out em_PINS_${net}.csv]
    psm::clear_solvers
    if {$::so_source eq "BUMPS"} {
        set src [file join $::so_out bumps_${net}.csv]
        set fh [open $src w]
        set p $::so_bump_pitch
        set nx [expr {max(1, int(floor(($dx1 - $dx0) / $p)))}]
        set ny [expr {max(1, int(floor(($dy1 - $dy0) / $p)))}]
        set ox [expr {$dx0 + (($dx1 - $dx0) - ($nx - 1) * $p) / 2.0}]
        set oy [expr {$dy0 + (($dy1 - $dy0) - ($ny - 1) * $p) / 2.0}]
        set nb 0
        for {set i 0} {$i < $nx} {incr i} {
            for {set j 0} {$j < $ny} {incr j} {
                set is_vdd [expr {(($i + $j) % 2) == 0}]
                if {($net eq "VDD") != $is_vdd && !($nx == 1 && $ny == 1)} { continue }
                set v [expr {$net eq "VDD" ? $::so_vdd : 0.0}]
                puts $fh "[expr {$ox + $i * $p}],[expr {$oy + $j * $p}],$::so_bump_size,$v"
                incr nb
            }
        }
        close $fh
        emit ir.bumps.$net $nb
        analyze_power_grid -net $net -vsrc $src -voltage_file $vf -enable_em -em_outfile $ef
    } else {
        analyze_power_grid -net $net -voltage_file $vf -enable_em -em_outfile $ef
    }
}
