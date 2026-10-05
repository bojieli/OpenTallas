set ::so_libs {{/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz} {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz} {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz} {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz} {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib} {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_DFFHQNH2V2X_RVT_SS_nldm_FAKE.lib} {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_DFFHQNV2X_RVT_SS_nldm_FAKE.lib}}
set ::so_odb /so_res/6_final.odb
set ::so_sdc /so_res/6_final.sdc
set ::so_spef {/so_res/6_final.spef}
set ::so_platform /OpenROAD-flow-scripts/flow/platforms/asap7
set ::so_pdn_tcl {}
set ::so_saif {}
set ::so_saif_scope {}
set ::so_groups {}
set ::so_inst_power {}
set ::so_derate 0.0
set ::so_vdd 0.63
set ::so_bump_pitch 140
set ::so_bump_size 50
set ::so_out /so_out/SS
file mkdir /so_out/SS

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
set_cmd_units -time ns -power W

emit corner.name SS


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


# -- timing at this corner -------------------------------------------------
emit timing.setup_wns_s [sta::worst_slack_cmd max]
emit timing.hold_wns_s [sta::worst_slack_cmd min]
emit timing.setup_tns_s [sta::total_negative_slack_cmd max]
emit timing.hold_tns_s [sta::total_negative_slack_cmd min]
report_clock_min_period
if {$::so_derate > 0} {
    set_timing_derate -early [expr {1.0 - $::so_derate}]
    set_timing_derate -late [expr {1.0 + $::so_derate}]
    emit timing_ocv.setup_wns_s [sta::worst_slack_cmd max]
    emit timing_ocv.hold_wns_s [sta::worst_slack_cmd min]
    report_clock_min_period
    unset_timing_derate
}
