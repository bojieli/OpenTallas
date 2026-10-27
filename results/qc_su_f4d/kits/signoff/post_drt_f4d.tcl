# QC-SU-F4D POST_DETAIL_ROUTE_TCL: delete the temporary M6 keep-out obstructions of pre_drt_f4d.tcl (DRT-only aid; they
# must not reach fill, RCX or the abstract -- the abstract carries per-shape M6 OBS of the routed tree via abstract_m6.py)
set blk [ord::get_db_block]; set n 0
foreach ob [$blk getObstructions] { if {[[[$ob getBBox] getTechLayer] getName] eq "M6"} { odb::dbObstruction_destroy $ob; incr n } }
puts "OT_TREE_M6_KEEPOUT removed $n"
