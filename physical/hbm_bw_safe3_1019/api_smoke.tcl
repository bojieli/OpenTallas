# Fleet-only lightweight OpenDB smoke; no synthesis, placement or route.
# env INPUT_ODB names an existing diagnostic floorplan database.
read_db $::env(INPUT_ODB)
source [file join [file dirname [info script]] core_band.tcl]
set group [[ord::get_db_block] findGroup bw_safe3_core_cells]
set region [$group getRegion]
puts "BW_SAFE3_API_PASS region=[$region getName] cells=[llength [$group getInsts]] boxes=[llength [$region getBoundaries]]"
