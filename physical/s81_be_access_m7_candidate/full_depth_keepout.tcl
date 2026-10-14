# Same hook beforeGRT and afterDRT: create then remove ONLY these temporary OBS.
# Real routed metal remains in the final database/export. Full-depth clearance
# replaces the observed legacyhalf-depth access failure. M5 PG starts at1.296um.
set ::env(OT_PK_FRAC) 0
set ::env(OT_PK_HALO) 0.072
set ::env(OT_PK_ABOVE_ONLY) 1
source /src/physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl
