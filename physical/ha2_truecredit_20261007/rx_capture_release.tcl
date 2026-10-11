# Release only the macro-owned capture flops for row legalization after GPL.
set cb [ord::get_db_block]
set fh [open $::env(RESULTS_DIR)/ha2_capture_collar.txt r]
set names [split [read $fh] "\n"]
close $fh
foreach name $names {
  if {$name eq ""} continue
  set ff [$cb findInst $name]
  if {$ff eq "NULL" || $ff eq ""} { error "Capture disappeared before legalization: $name" }
  $ff setPlacementStatus PLACED
}
