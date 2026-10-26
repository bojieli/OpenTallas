# ds-coll 2026-10-12: PRE_GLOBAL_PLACE chain for the old-flow ceh tiles = pin flops at the face (io_flop_at_pins.tcl)
# THEN one input-hold pad per data input (leaf_inhold.tcl, VM8 181753c60: dont_touch HB4 hold cell + OT_INHOLD_DRV
# strong driver, both FIRM at the pin).  ces0 f9453c0d4 closed TT +41.06 but missed FF hold by -0.5 ps on 5
# input -> capture paths (hold repair stalled): deterministic delay stage at the inputs (owner 10-10), constraints unchanged.
# The flow copies step hooks to /work/hooks (95905d84e-ih cal: "/work/hooks/../../qwen_die_masters/io_flop_at_pins.tcl:
# no such file"), so resolve the two hooks from the repo mount (/src, as MACRO_PLACEMENT_TCL), else relative to the repo.
# Both hooks are plain top-level scripts without helper procs, so sourcing them in the caller's (proc) scope is what ORFS
# does when either is the PRE_GLOBAL_PLACE hook on its own.
foreach ot_ioih_rel {physical/qwen_die_masters/io_flop_at_pins.tcl physical/dsrom_window_source/leaf_inhold.tcl} {
  set ot_ioih_f ""
  foreach ot_ioih_root [list /src [file normalize [file join [file dirname [info script]] ../../..]] [pwd]] {
    if {[file exists [file join $ot_ioih_root $ot_ioih_rel]]} { set ot_ioih_f [file join $ot_ioih_root $ot_ioih_rel]; break }
  }
  if {$ot_ioih_f eq ""} { error "IOFLOP_INHOLD: $ot_ioih_rel not found under /src or the repo" }
  puts "IOFLOP_INHOLD: source $ot_ioih_f"
  source $ot_ioih_f
}
