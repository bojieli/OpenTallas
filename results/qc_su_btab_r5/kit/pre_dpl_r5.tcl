# QC-SU-BTAB-R5 PRE_DETAIL_PLACE: r4 releases (face pin registers, macro-pin flops), then drop the r5_e_logic INCLUSIVE
# region of pre_gpl_r5.tcl: GPL has already put its members in x 255-340; with the region kept, the two-domain
# negotiation legaliser left 9 cells overlapping tap cells (r5 try 3, DPL-0033).  DPL then legalises locally as usual.
source /work/pre_dpl_m0.tcl
set r5n 0
foreach g [[ord::get_db_block] getGroups] { if {[$g getName] eq "r5_e_logic"} { foreach i [$g getInsts] { $g removeInst $i; incr r5n }; odb::dbGroup_destroy $g } }
foreach r [[ord::get_db_block] getRegions] { if {[$r getName] eq "r5_e_logic"} { odb::dbRegion_destroy $r } }
puts "R5_E_LOGIC region released before DPL ($r5n members keep their GPL sites)"
