# QHUB-S1 10-19 (d4g kits hbm_hcq_hub_s1 / hbm_hcq_hub_s1b; from the P3 HUB-SAFE hub_band_gpl.tcl, claude/hnx-hub-safe-1019): PRE_GLOBAL_PLACE.
# The HC quarter hub sits in the 734.4 um hole of the 3x3 bank ring (die slot, 10.1k face pins) but holds only ~50k um2
# of logic + one SRAM.  n2 (closure job hnx_hcq_hub_1019-n2-3af689b62) spread 48,778 registers over the whole square and
# anchored every pin flop at its face: pin-flop clock spread 151 ps TT / 134 ps FF -> EARLY_FAIL_HOLD at FF.
# Safe form: ONE central standard-cell band (OT_HUB_BAND = x0,y0,x1,y1 um) holds every synthesized standard cell
# (pin registers included), so the single clock tree serves a compact register mass; the face pins are <= ~390 um from
# the band (one registered hop, reach 405), the collar carries only the pin wires and their repeaters.
# The band is a GLOBAL-PLACEMENT region only: hub_band_dpl.tcl (PRE_DETAIL_PLACE) removes it again, so detailed placement,
# CTS and repair legalise freely (the 10-19 P3 ATT gate crashed DPL inside an EXCLUSIVE region: no region reaches DPL here).
set hb_blk [ord::get_db_block]
set hb_dbu [$hb_blk getDbUnitsPerMicron]
if {![info exists ::env(OT_HUB_BAND)]} { error "hc_hub_band_gpl: OT_HUB_BAND (x0,y0,x1,y1 um) not set" }
lassign [split $::env(OT_HUB_BAND) ","] hb_x0 hb_y0 hb_x1 hb_y1
set hb_reg [$hb_blk findRegion hc_hub_band]
if {$hb_reg eq "NULL"} {
    set hb_reg [odb::dbRegion_create $hb_blk hc_hub_band]
    $hb_reg setRegionType INCLUSIVE
    odb::dbBox_create $hb_reg [expr {round($hb_x0*$hb_dbu)}] [expr {round($hb_y0*$hb_dbu)}] [expr {round($hb_x1*$hb_dbu)}] [expr {round($hb_y1*$hb_dbu)}]
}
set hb_grp [$hb_blk findGroup hc_hub_band]
if {$hb_grp eq "NULL"} { set hb_grp [odb::dbGroup_create $hb_reg hc_hub_band] }
set hb_in 0; set hb_out 0
foreach hb_i [$hb_blk getInsts] {
    set hb_m [$hb_i getMaster]
    if {[$hb_m isBlock] || [$hb_i isFixed] || [$hb_i getPlacementStatus] eq "FIRM"} { continue }
    # tie cells stay outside (no clock, no timing): the top-level placer keeps a non-empty population
    if {[string match "TIE*" [$hb_m getName]]} { incr hb_out; continue }
    $hb_grp addInst $hb_i
    incr hb_in
}
if {$hb_in < 1000} { error "hc_hub_band_gpl: only $hb_in cells in the band" }
puts "HC_HUB_BAND gpl region ($hb_x0,$hb_y0)-($hb_x1,$hb_y1) um: $hb_in cells in the band, $hb_out tie cells outside"
