
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef

read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz

read_db /input/6_final.odb
read_sdc /input/6_final.sdc
read_spef /input/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /src/physical/s81_ph_views/common/signoff_unc60.sdc

set patch_out {/case/candidate}
set patches {
  {g_r[12].u_x.w_st_r[0]$_DFF_P_/D} {HB3xp67_ASAP7_75t_R}
}
# Exact leaf-only buffer insertion. Timing after mutation is deliberately NOT
# used as a verdict: the runner launches fresh SS and FF processes on the output.
set block [ord::get_db_block]
if {[$block getName] ne "dsfd_capt_x"} {error "Wrong capture design"}
set dbu [$block getDbUnitsPerMicron]
set ordinal 0
set_thread_count 16
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
if {![grt::have_routes]} {error "Original routing guides required"}
remove_fillers
set_global_routing_layer_adjustment M2-M7 0.25
set_routing_layers -signal M2-M7 -clock M4-M7
global_route -start_incremental
foreach {endpoint masters} $patches {
  set pins {}
  foreach p [get_pins -hierarchical */D] {
    if {[get_full_name $p] eq $endpoint} {lappend pins $p}
  }
  if {[llength $pins] != 1} {error "STA/ODB endpoint identity mismatch $endpoint"}
  # STA prints brackets without the escapes retained by OpenDB. Resolve the
  # unique literal STA pin directly, without rewriting or globbing its name.
  if {![llength [info commands sta::sta_to_db_pin]]} {error "STA/ODB pin mapping unavailable"}
  set d [sta::sta_to_db_pin [lindex $pins 0]]
  if {$d eq "NULL" || $d eq ""} {error "No mapped data terminal $endpoint"}
  set sink [$d getInst]
  if {$sink eq "NULL" || [$sink findITerm D] ne $d ||
      [[$sink getMaster] getName] ne "DFFHQNx1_ASAP7_75t_R"} {
    error "Mapped endpoint is not the original startup data terminal $endpoint"
  }
  puts "S81_STARTUP_IDENTITY sta=$endpoint odb=[$sink getName] pin=D"
  foreach master $masters {
    set original [$d getNet]
    set name s81_startup_hold_$ordinal
    if {[$block findInst $name] ne "NULL"} {error "Patch already applied"}
    lassign [$sink getLocation] x y
    insert_buffer -buffer_cell $master -load_pins $pins \
      -buffer_name $name -net_name s81_startup_net_$ordinal \
      -location [list [expr {double($x)/$dbu}] [expr {double($y)/$dbu}]]
    puts "INSERT_RESULT requested=$name requested_master=$master exact=[$block findInst $name]"
    foreach i [$block getInsts] {
      if {[string match *s81_startup* [$i getName]]} {
        puts "INSERT_INSTANCE name=[$i getName] master=[[$i getMaster] getName]"
      }
    }
    puts "SINK_NET [[$d getNet] getName]"
    foreach t [[$d getNet] getITerms] {puts "SINK_NET_PIN [[$t getInst] getName]/[[$t getMTerm] getName]"}
    exit
  }
}
