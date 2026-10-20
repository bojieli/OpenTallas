read_db $::env(PVM_BF_AUDIT_ODB)
set pvm_bf_stage $::env(PVM_BF_AUDIT_STAGE)
source [file join [file dirname [info script]] stage_guard.tcl]
