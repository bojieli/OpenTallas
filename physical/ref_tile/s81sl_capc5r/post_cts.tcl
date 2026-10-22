source /src/physical/ref_tile/s81sl_capc5r/clock_entry.sdc

# DRIVE-S81-CAP: post-CTS refine of hard-child chains to the region soft centre (after DPL + hold repair)
if {![llength [info procs ot_rtb_refine]]} { set ::ot_rtb_offline 1; source /src/physical/ref_tile/s81sl_capc5r/rt_leaf_balance.tcl }
if {[catch {ot_rtb_refine} ot_rtb_e]} { puts "OT_RTB_REFINE ERROR (db kept): $ot_rtb_e" }
