read_db /work/run/results/asap7/hc_qkd_hr_phy_adp__103_68x95_04/base/4_cts.odb
source /work/output_hold_guard_procs.tcl
set ref {};foreach i [[ord::get_db_block] getInsts] {dict set ref [$i getName] [list [[$i getMaster] getName] [$i getOrient] [$i getLocation]]}
set f [open /work/output_hold1/original_physical_reference.tcl w]
puts $f [list set oh_orig $ref];puts $f [list set oh_orig_pins [oh_pins]];puts $f [list set oh_orig_pg [oh_pg_wires]];close $f
puts PHY_ORIGINAL_PHYSICAL_REFERENCE_DONE
