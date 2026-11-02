# Candidate allFF guard: run after native target application and at PRE_DETAIL_PLACE.
uplevel #0 {
set af_targets {}
set af_f [open /work/allFF_targets.tsv r]
while {[gets $af_f af_l] >=0} {
  lassign [split $af_l "	"] af_n af_m af_x af_y af_o
  dict set af_targets $af_n [list $af_m $af_x $af_y $af_o]
}
close $af_f
if {[dict size $af_targets] !=31847} {error "allFF target cardinality"}
set af_hits {}
foreach af_i [[ord::get_db_block] getInsts] {
  set af_n [string map [list [format %c 92] {}] [$af_i getName]]
  if {![dict exists $af_targets $af_n]} continue
  if {[dict exists $af_hits $af_n]} {error "allFF duplicate identity $af_n"}
  lassign [dict get $af_targets $af_n] af_m af_x af_y af_o
  lassign [$af_i getLocation] af_ix af_iy
  if {[[$af_i getMaster] getName] ne $af_m || $af_ix !=$af_x || $af_iy !=$af_y || [$af_i getOrient] ne $af_o} {
    error "allFF native target moved/master/orientation changed $af_n"
  }
  $af_i setPlacementStatus FIRM
  $af_i setDoNotTouch 1
  dict set af_hits $af_n 1
}
if {[dict size $af_hits] !=31847} {error "allFF identities missing"}
puts "ALLFF guard31847 FIRM/dont_touch, exact master/location/orientation"
}
