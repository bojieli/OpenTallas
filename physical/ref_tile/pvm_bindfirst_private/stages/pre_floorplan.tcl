set pvm_bf_stage pre_floorplan
source [file join [file dirname [info script]] .. stage_guard.tcl]
source $::env(PVM_BF_MANDATORY_NATIVE)
