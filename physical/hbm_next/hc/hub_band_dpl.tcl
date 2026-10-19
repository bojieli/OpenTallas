# HUB-SAFE 10-19: PRE_DETAIL_PLACE.  Remove the global-placement band (hub_band_gpl.tcl) before legalisation: the cells
# are already in the band; DPL / CTS / repair legalise without a region (no region type reaches the legaliser).
set hb_blk [ord::get_db_block]
set hb_grp [$hb_blk findGroup hnx_hub_band]
set hb_n 0
if {$hb_grp ne "NULL"} {
    foreach hb_i [$hb_grp getInsts] { $hb_grp removeInst $hb_i; incr hb_n }
    odb::dbGroup_destroy $hb_grp
}
set hb_reg [$hb_blk findRegion hnx_hub_band]
if {$hb_reg ne "NULL"} { odb::dbRegion_destroy $hb_reg }
puts "HNX_HUB_BAND dpl: band region removed ($hb_n cells released)"
