source /work/sc_guard.tcl
source /work/sc_guard_state.tcl
sc_check before_dpl firm
source /work/face_flops_release.tcl
sc_restore_and_lock
sc_check normal_pre_dpl_restored firm
