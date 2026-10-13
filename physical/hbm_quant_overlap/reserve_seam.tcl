# POST_TAPCELL: preserve the OBS-screened central decoder seam against standard-cell placement.
# Signal routing uses this clear 300um span; gather/result routes remain regional.
set ov_block [ord::get_db_block]
set ov_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
odb::dbBlockage_create $ov_block [expr {int(round(270.0*$ov_dbu))}] [expr {int(round(336.96*$ov_dbu))}] [expr {int(round(570.0*$ov_dbu))}] [expr {int(round(388.8*$ov_dbu))}]
puts "OT_QUANT_SEAM reserved x270..570 y336.96..388.8 (300um central decoder seam)"
