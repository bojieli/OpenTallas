# PRE_TAPCELL: preserve the OBS-screened central decoder seam against standard-cell placement.
# Reserve before tap/endcap insertion so fixed cells occupy surviving rows only.
# Signal routing uses this clear 300um span; gather/result routes remain regional.
set ov_block [ord::get_db_block]
set ov_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
odb::dbBlockage_create $ov_block [expr {int(round(270.0*$ov_dbu))}] [expr {int(round(336.96*$ov_dbu))}] [expr {int(round(570.0*$ov_dbu))}] [expr {int(round(388.8*$ov_dbu))}]
# Native ASAP7 tapcell cuts macro halos, not dbBlockages. Split the site rows now,
# before fixed endcaps/taps are inserted; otherwise GPL later removes occupied rows.
set ov_xlo [expr {int(round(270.0*$ov_dbu))}]
set ov_xhi [expr {int(round(570.0*$ov_dbu))}]
set ov_ylo [expr {int(round(336.96*$ov_dbu))}]
set ov_yhi [expr {int(round(388.8*$ov_dbu))}]
set ov_cut_rows 0
foreach ov_row [$ov_block getRows] {
    set ov_box [$ov_row getBBox]
    if {[$ov_box yMax] <= $ov_ylo || [$ov_box yMin] >= $ov_yhi ||
        [$ov_box xMax] <= $ov_xlo || [$ov_box xMin] >= $ov_xhi} {continue}
    if {[$ov_row getDirection] ne "HORIZONTAL"} {error "quant seam requires horizontal native rows"}
    lassign [$ov_row getOrigin] ov_x ov_y
    set ov_n [$ov_row getSiteCount]
    set ov_pitch [$ov_row getSpacing]
    set ov_site [$ov_row getSite]
    set ov_orient [$ov_row getOrient]
    set ov_name [$ov_row getName]
    set ov_left [expr {max(0,min($ov_n,int(floor(double($ov_xlo-$ov_x)/$ov_pitch))))}]
    set ov_right_i [expr {max(0,min($ov_n,int(ceil(double($ov_xhi-$ov_x)/$ov_pitch))))}]
    if {$ov_left > 0} {
        odb::dbRow_create $ov_block [format "%s_SEAM_L" $ov_name] $ov_site $ov_x $ov_y $ov_orient HORIZONTAL $ov_left $ov_pitch
    }
    if {$ov_right_i < $ov_n} {
        odb::dbRow_create $ov_block [format "%s_SEAM_R" $ov_name] $ov_site [expr {$ov_x+$ov_right_i*$ov_pitch}] $ov_y $ov_orient HORIZONTAL [expr {$ov_n-$ov_right_i}] $ov_pitch
    }
    odb::dbRow_destroy $ov_row
    incr ov_cut_rows
}
foreach ov_row [$ov_block getRows] {
    set ov_box [$ov_row getBBox]
    if {[$ov_box yMax] > $ov_ylo && [$ov_box yMin] < $ov_yhi &&
        [$ov_box xMax] > $ov_xlo && [$ov_box xMin] < $ov_xhi} {
        error "quant seam retained intersecting row [$ov_row getName]"
    }
}
puts "OT_QUANT_SEAM native_rows_split=$ov_cut_rows before tap/endcap insertion"
puts "OT_QUANT_SEAM reserved x270..570 y336.96..388.8 (300um central decoder seam)"
