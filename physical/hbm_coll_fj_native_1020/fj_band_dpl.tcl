# FJ native32 literal-grid plan; keep all generated pin/hold hooks in each kit wrapper.
# Reused QHUB central-band placement contract; all cells released before DPL.
# QHUB-S1 10-19 (d4g hub kits, from the P3 HUB-SAFE hub_band_dpl.tcl): PRE_DETAIL_PLACE.  Remove the global-placement band (fj_std_band_gpl.tcl) before legalisation: the cells
# are already in the band; DPL / CTS / repair legalise without a region (no region type reaches the legaliser).
set hb_blk [ord::get_db_block]
set hb_grp [$hb_blk findGroup fj_std_band]
set hb_n 0
if {$hb_grp ne "NULL"} {
    foreach hb_i [$hb_grp getInsts] { $hb_grp removeInst $hb_i; incr hb_n }
    odb::dbGroup_destroy $hb_grp
}
set hb_reg [$hb_blk findRegion fj_std_band]
if {$hb_reg ne "NULL"} { odb::dbRegion_destroy $hb_reg }
puts "FJ_STD_BAND dpl: band region removed ($hb_n cells released)"
