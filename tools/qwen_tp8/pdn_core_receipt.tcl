# Read-only core-origin receipt for an existing completed database.
read_db $::env(OT_PDN_ODB)
set b [ord::get_db_block]
set u [$b getDbUnitsPerMicron]
set c [$b getCoreArea]
set d [$b getDieArea]
puts "CORE_RECEIPT dbu=$u core_dbu=[$c xMin],[$c yMin],[$c xMax],[$c yMax] die_dbu=[$d xMin],[$d yMin],[$d xMax],[$d yMax]"
