read_db /in/4_cts.odb
source /probe/vmcore_pins.tcl
set probe_blk [ord::get_db_block];set initial [llength [$probe_blk getObstructions]]
set ::env(OT_PK_HALO) 6.48;set ::env(OT_PK_FRAC) 0;set ::env(OT_PK_ABOVE_ONLY) 1
source /src/physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl
set ::ot_smpub_corridor_pin {i_v[1]};set ::ot_smpub_corridor_half 0.864;set ::ot_smpub_corridor_post 0
source /probe/pin_corridor.tcl
set during [llength [$probe_blk getObstructions]]
source /src/physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl
set ::ot_smpub_corridor_post 1;source /probe/pin_corridor.tcl
if {[llength [$probe_blk getObstructions]]!=$initial} {error "corridor left artificial OBS: [$probe_blk getObstructions]"}
puts "PASS corridor actual ODB created real access and removed all temporary OBS ($initial -> $during -> $initial)"
