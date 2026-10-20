# PRE_GLOBAL_PLACE companion of reach_reloc.tcl (QW-N59SVC 2026-10-20): no placement change; checks that the
# PRE_DETAIL_PLACE reach relocation can run (script present) before global placement spends hours.
if {![file exists /src/physical/qwen_die_masters/reach_reloc.py]} { error "OT_REACH_RELOC: /src/physical/qwen_die_masters/reach_reloc.py missing" }
puts "OT_REACH_RELOC armed: reach [expr {[info exists ::env(OT_REACH_RELOC_UM)] ? $::env(OT_REACH_RELOC_UM) : 390}] um"
