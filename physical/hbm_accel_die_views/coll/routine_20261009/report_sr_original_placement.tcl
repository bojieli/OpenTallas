# Actual placement checker only; original ODB read-only, no placement change.
read_db $::env(OT_FAILED_ODB)
set rc [catch {check_placement -verbose -report_file_name /inspect/sr-original-placement-markers.json} err]
puts "SR_ORIGINAL_GEOMETRY_CHECK rc=$rc detail=$err"
exit
