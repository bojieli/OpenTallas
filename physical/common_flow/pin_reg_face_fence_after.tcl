# TILE-FLOW 10-23: PRE_GLOBAL_PLACE wrapper for kits that already own a PRE_GLOBAL_PLACE hook (die-fixed clusters such as
# the HBM HC qhub): run that hook first (OT_FENCE_PRE_HOOK, a /src path; empty = none), then fence every pin register in
# its face band (pin_reg_face_fence.tcl).  ORFS takes one hook per step, so this file chains the two.
if {[info exists ::env(OT_FENCE_PRE_HOOK)] && $::env(OT_FENCE_PRE_HOOK) ne ""} {
  source $::env(OT_FENCE_PRE_HOOK)
}
source [file join [file dirname [file normalize [info script]]] pin_reg_face_fence.tcl]
