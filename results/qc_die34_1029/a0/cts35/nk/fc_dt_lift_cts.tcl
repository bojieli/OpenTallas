# DIE-QC-35 (A0) PRE_CTS hook = the gen_core_kit_qc.py (main) hold_budget.tcl lift, without its repair_timing override:
# this kit has insertion_balance off, so the generator never emitted it and CTS stopped on ODB-0370 (dont_touch CLK
# of ot_fconst_00001_ff, cts_FAIL1_odb0370.log). CTS must reconnect the CLK of the POST_SYNTH capture / constant flops
# (ot_fcap_* / ot_fconst_*); per QC-CORES r3 dont_touch stays lifted after CTS; signoff face_guard re-checks them.
set ::ot_fc_dt {}
foreach i [[ord::get_db_block] getInsts] { if {[regexp {^ot_fc(ap|onst)_} [$i getName]] && [$i isDoNotTouch]} { $i setDoNotTouch 0; lappend ::ot_fc_dt [$i getName] } }
puts "OT_FCAP: dont_touch lifted for CTS on [llength $::ot_fc_dt] flops"
