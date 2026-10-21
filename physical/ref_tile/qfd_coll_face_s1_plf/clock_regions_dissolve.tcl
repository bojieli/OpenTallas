# QW-TREE-SAFE 10-21: dissolve the ot_cr_* clock-region groups after GPL + resize (their placement already encodes the
# fence); DPL then legalises locally and later repair / CTS buffers have a legal home (QW-TTC8 safe8u lesson).
set ot_crd_block [ord::get_db_block]
set ot_crd_ng 0; set ot_crd_nr 0; set ot_crd_m 0
foreach g [$ot_crd_block getGroups] {
    if {![string match ot_cr_* [$g getName]]} continue
    foreach i [$g getInsts] {$g removeInst $i; incr ot_crd_m}
    odb::dbGroup_destroy $g
    incr ot_crd_ng
}
foreach r [$ot_crd_block getRegions] {
    if {![string match ot_cr_* [$r getName]]} continue
    odb::dbRegion_destroy $r
    incr ot_crd_nr
}
if {$ot_crd_ng != 2 || $ot_crd_nr != 2} {error "OT_CRD expected 2 ot_cr groups / regions, found $ot_crd_ng / $ot_crd_nr"}
puts "OT_CRD PASS dissolved $ot_crd_ng groups / $ot_crd_nr regions ($ot_crd_m members keep their GPL placement)"
