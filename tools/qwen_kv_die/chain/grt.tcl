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
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set_routing_layers -signal M4-M9 -clock M4-M9
set_global_routing_layer_adjustment M4-M5 0.30
set_global_routing_layer_adjustment M6-M9 0.05
# r22 adjfix: no PG-proxy region adjustments (the physical r5 PDN is in the odb; 0.146 = 0.05 via + 2 x 0.0439 PG proxy double-counted it)
step special {
  # die clock / reset / forwarded-clock nets are built by the die clock tree (CTS), not the signal router
  set n 0
  foreach net [[ord::get_db_block] getNets] {
    if {[regexp {^n_(clk_|fck_|rst_)} [$net getName]]} { $net setSpecial; incr n }
  }
  puts "OT_SPECIAL clock_reset_nets=$n"
}
step grt { global_route -congestion_iterations $::env(OT_ITERS) -allow_congestion -verbose -congestion_report_file /work/grt_congestion.rpt }
step guides { write_guides /work/route.guide }
step ckpt { write_db /work/ckpt_grt.odb }
step wl { report_wire_length -net * -global_route -file /work/wirelength.csv }
# die-evidence-2 2026-10-09: GRT parasitics are extracted HERE, in the routing session, and written as SPEF. A later
# session cannot get them from the guides: read_guides + estimate_parasitics -global_routing gives NO wire RC (GRT-0008),
# so every die STA that did that timed the die with zero wire load.  sta_tcl.py reads this SPEF instead.
step spef { estimate_parasitics -global_routing; write_spef /work/die_grt.spef }
puts OT_GRT_DONE
