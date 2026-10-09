set f [open $::env(OT_SR_METADATA_FILE) r]
gets $f first;eval $first
gets $f second;eval $second
close $f
set f [open $::env(OT_SR_ANCHOR_NAMES) w]
foreach name [dict keys $anchor_meta] {puts $f "$name\t[dict exists $released $name]"}
close $f
