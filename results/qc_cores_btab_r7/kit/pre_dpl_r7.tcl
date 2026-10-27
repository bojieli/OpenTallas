# QC-CORES-1 btab_m0_r7 PRE_DETAIL_PLACE: r4 releases (face pin registers, macro-pin flops), then drop every r7_mux_* INCLUSIVE
# region of pre_gpl_r7.tcl (r5 try 3: regions kept in DPL -> tap overlaps).  GPL has already put the members in their grid cells.
source /work/pre_dpl_m0.tcl
set r7n 0; set r7g 0
foreach g [[ord::get_db_block] getGroups] { if {[string match r7_mux_* [$g getName]]} { foreach i [$g getInsts] { $g removeInst $i; incr r7n }; odb::dbGroup_destroy $g; incr r7g } }
foreach r [[ord::get_db_block] getRegions] { if {[string match r7_mux_* [$r getName]]} { odb::dbRegion_destroy $r } }
puts "R7_MUX_GRID $r7g regions released before DPL ($r7n members keep their GPL sites)"
