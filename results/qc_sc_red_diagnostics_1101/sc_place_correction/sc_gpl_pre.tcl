source /work/sc_guard.tcl
source /work/sc_guard_state.tcl
sc_check before_gpl original
source /work/face_flops.tcl
sc_restore_and_lock
sc_check normal_pre_gpl_restored firm
