# Pure metadata membership audit; no OpenROAD/design mutation or timing run.
set f [open $::env(OT_SR_METADATA_FILE) r]
gets $f first;eval $first
gets $f second;eval $second
close $f
set f [open $::env(OT_SR_VIOLATION_NAMES) r]
set n 0;set rel 0;set examples 0
while {[gets $f name]>=0} {
 if {![dict exists $anchor_meta $name]} continue
 incr n
 if {[dict exists $released $name]} {incr rel} elseif {$examples<12} {puts "SR_FIXED_ANCHOR_ORIGINAL_EDGE_VIOLATION $name";incr examples}
}
close $f
puts "SR_ORIGINAL_EDGE_LIST_ANCHORS total=$n released=$rel fixed=[expr {$n-$rel}]"
