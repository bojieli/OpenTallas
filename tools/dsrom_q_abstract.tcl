# DSROM q-element abstract from a routed element (2026-10-04): read the final odb, remove the routing obstructions the
# element flow placed (physical/abi3/dsrom_q_pin_keepout.tcl: a routing constraint, not metal), and write the abstract
# exactly as the S81 die's q abstract was written (results/uarch/dsrom_c_w4_20261003/s82_combined_r1/routed_q/extract.tcl:
# write_abstract_lef, default options).  env: ODB, OUT (lef path).
read_db $::env(ODB)
set blk [ord::get_db_block]
set n 0
foreach o [$blk getObstructions] { odb::dbObstruction_destroy $o; incr n }
puts "OT_ABSTRACT removed_obstructions=$n"
write_abstract_lef $::env(OUT)
puts "OT_ABSTRACT_DONE"
