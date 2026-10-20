source /src/physical/qwen_die_masters/post_plain.tcl

source /src/physical/ref_tile/dsdv_mu_hwin_c21j/hwin_native_fences.tcl
ot_hj_fences_install
ot_hj_assign_births 0
ot_hj_fences_check post_cts.tcl
