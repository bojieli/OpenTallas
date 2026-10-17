# adjfix (2026-10-07 qwen-dietop): physical PDN present -> M6-M9 adjustment = VIA_OBS 0.05 only; PG-proxy region adjustments dropped
# Full-die r20c top-level GRT (owner 2026-10-06): signals on M4..M9 only (M1-M3 belong to the elements; every element
# signal pin is on M4/M5/M6/M8), coarse gcell grid (GRT tile = 15 x M2 track pitch in this build: M2/M3 carry no die
# signal, so their track grids are re-pitched to set the tile; OT_TILE_UM), r20c per-layer + corridor region capacity
# adjustments (M6-M9 0.146, corridor M8/M9 0.53 / 0.1033 as the r20c bundled GRT; M4/M5 0.30 kept for element pin escape).
proc mem {tag} { set f [open /proc/self/status]; set s [read $f]; close $f
  regexp {VmRSS:\s+(\d+)} $s -> r; regexp {VmHWM:\s+(\d+)} $s -> h
  puts "OTMEM $tag rss_mb=[expr {$r/1024}] hwm_mb=[expr {$h/1024}] t=[clock seconds]"; flush stdout }
proc step {name body} { set t0 [clock milliseconds]
  if {[catch {uplevel 1 $body} err]} { puts "OT_STEP_FAIL $name $err"; flush stdout }
  puts "OT_TIME step=$name s=[format %.1f [expr {([clock milliseconds]-$t0)/1000.0}]]"; mem $name }
set_thread_count $::env(OT_THREADS)
step load { read_db /work/floorplan_pdn.odb }
step coarse {
  # dbBlock::getGCellTileSize = 15 x median(track pitch of M2, M3, M4): re-pitch M2 and M3 (no die signal on either)
  set b [ord::get_db_block]; set p [expr {$::env(OT_TILE_UM)/15.0}]
  foreach ln {M2 M3} { odb::dbTrackGrid_destroy [$b findTrackGrid [[ord::get_db_tech] findLayer $ln]]
    make_tracks $ln -x_offset 0.009 -x_pitch $p -y_offset 0.009 -y_pitch $p }
  puts "OT_TILE dbu=[$b getGCellTileSize]"
}
# DIE-FLOW 10-17 (owner 0cl): OT_DIE_REPAIR=1 -> the shared die-net repeater step before GRT (die_chain.sh writes
# /work/die_rep_call.tcl: tools/die_repeaters, element + std TT libs, buffers only, registers/relays checked unchanged,
# clock / forwarded-clock / reset nets untouched); the STA reads the repaired netlist from ckpt_grt.odb.
if {[info exists ::env(OT_DIE_REPAIR)] && $::env(OT_DIE_REPAIR) == 1} {
  set t0 [clock milliseconds]
  if {[catch {source /work/die_rep_call.tcl} err]} { puts "OT_STEP_FAIL repeaters $err"; flush stdout; exit 3 }
  puts "OT_TIME step=repeaters s=[format %.1f [expr {([clock milliseconds]-$t0)/1000.0}]]"; mem repeaters
} else {
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
}
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set_routing_layers -signal M4-M9 -clock M4-M9
set_global_routing_layer_adjustment M4-M5 0.30
set_global_routing_layer_adjustment M6-M9 0.05
# r22 adjfix: no PG-proxy region adjustments (the physical r5 PDN is in the odb; 0.146 = 0.05 via + 2 x 0.0439 PG proxy double-counted it)
step special {
  # die clock / reset / forwarded-clock nets are built by the die clock tree (CTS), not the signal router
  set n 0
  foreach net [[ord::get_db_block] getNets] {
    # die lead r9 2026-10-13: with the registered reset tree every reset net is an ordinary <= 500 um registered hop
    # between repeaters and is ROUTED (OT_ROUTE_RESET=1); only the clocks stay with CTS
    if {[info exists ::env(OT_ROUTE_RESET)] && $::env(OT_ROUTE_RESET) == 1} { set pat {^n_(clk_|fck_)} } else { set pat {^n_(clk_|fck_|rst_)} }
    if {[regexp $pat [$net getName]]} { $net setSpecial; incr n }
  }
  puts "OT_SPECIAL clock_reset_nets=$n"
}
step grt { global_route -congestion_iterations $::env(OT_ITERS) -allow_congestion -verbose -congestion_report_file /work/grt_congestion.rpt }
# die readout (owner 10-16): GRT routing-usage heat map, 50 um bins, for tools/qwen_split/die_readout.py
step heat { catch {gui::set_heatmap Routing GridX 50}; catch {gui::set_heatmap Routing GridY 50}; gui::dump_heatmap Routing /work/grt_heatmap.csv }
step guides { write_guides /work/route.guide }
step ckpt { write_db /work/ckpt_grt.odb }
step wl { report_wire_length -net * -global_route -file /work/wirelength.csv }
# die-evidence-2 2026-10-09 / ds-1010 2026-10-10: GRT parasitics are written as SPEF by the RESIZER
# (estimate_parasitics -spef_file).  'write_spef' is the RCX writer and fails with RCX-0134 (no extraction data) after
# a global route, which left every Qwen die without STA.  If this step is lost, spef_from_ckpt.tcl rebuilds the same
# SPEF from ckpt_grt.odb: write_db keeps the global routes (grt::have_routes = 1 after read_db) and the reloaded
# estimate is identical to the in-session one (checked net by net, 2026-10-10).
step spef { estimate_parasitics -global_routing -spef_file /work/die_grt.spef }
# empty *PORTS (no top ports) breaks OpenSTA read_spef (STA-1670): drop it
step ports { exec sed -i {1,40{/^\*PORTS$/{N;/^\*PORTS\n$/d}}} /work/die_grt.spef }
if {![file exists /work/die_grt.spef] || [file size /work/die_grt.spef] == 0} { puts "OT_STEP_FAIL spef not written"; exit 3 }
puts OT_GRT_DONE
