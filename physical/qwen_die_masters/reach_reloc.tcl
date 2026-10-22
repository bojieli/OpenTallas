# PRE_DETAIL_PLACE hook (QW-N59SVC 2026-10-20): register-stage reach repair, 0 added cycles.  Runs after the pin flops
# are released (out_flop_release.tcl).  Writes the global-placement ODB, runs reach_reloc.py (actual Liberty stage graph:
# FF/macro/port -> FF/macro/port with every combinational function collapsed, clock pins excluded, async reset kept) and
# moves each register whose longest stage endpoint span exceeds OT_REACH_RELOC_UM (default 390, planning reach 405) to the
# L1 minimax centre of its stage neighbours, so existing registers become forwarded hops; DPL legalises them next.
# Why: qfd_n59_svc3 3_5 placement (Codex audit 0c21c3724) had 246 data + 37 reset endpoint spans > 405 um in the
# 518.4 x 216 pin-bound outline (rx pin regs west vs the record codec east, emb scale relay, dvf -> fault, reset relays).
# OT_REACH_RELOC_STRICT=1 (default): residual spans > 405 after relocation are an error (the gate must not hide them).
set ot_rr_blk [ord::get_db_block]
set ot_rr_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ot_rr_reach [expr {[info exists ::env(OT_REACH_RELOC_UM)] && $::env(OT_REACH_RELOC_UM) ne "" ? $::env(OT_REACH_RELOC_UM) : 390}]
set ot_rr_strict [expr {!([info exists ::env(OT_REACH_RELOC_STRICT)] && $::env(OT_REACH_RELOC_STRICT) eq "0")}]
set ot_rr_py /src/physical/qwen_die_masters/reach_reloc.py
set ot_rr_in $::env(RESULTS_DIR)/ot_reach_reloc_in.odb
set ot_rr_tsv $::env(RESULTS_DIR)/ot_reach_reloc_moved.tsv
set ot_rr_sum $::env(RESULTS_DIR)/ot_reach_reloc_summary.json
set ot_rr_exe [expr {[info exists ::env(OPENROAD_EXE)] ? $::env(OPENROAD_EXE) : [info nameofexecutable]}]
write_db $ot_rr_in
if {[catch {exec $ot_rr_exe -python -exit $ot_rr_py $ot_rr_in $ot_rr_tsv $ot_rr_sum $::env(PLATFORM_DIR) $ot_rr_reach 8 2>@1} ot_rr_log]} {
  puts $ot_rr_log
  if {![file exists $ot_rr_sum]} { error "OT_REACH_RELOC: reach_reloc.py failed" }
}
puts $ot_rr_log
file delete -force $ot_rr_in
set ot_rr_n 0
set fh [open $ot_rr_tsv r]
foreach ln [split [read $fh] "\n"] {
  if {$ln eq ""} continue
  # names carry literal backslashes (u_x.dvf\[2\]$_DFFE_): split on spaces, never Tcl list parsing
  if {![regexp {^(\S+) (\S+) (\S+)$} $ln -> nm x y]} { error "OT_REACH_RELOC: bad line $ln" }
  set i [$ot_rr_blk findInst $nm]
  if {$i eq "NULL" || $i eq ""} { error "OT_REACH_RELOC: instance $nm not found" }
  $i setLocation [expr {round($x * $ot_rr_dbu)}] [expr {round($y * $ot_rr_dbu)}]
  $i setPlacementStatus PLACED
  incr ot_rr_n
}
close $fh
puts "OT_REACH_RELOC moved $ot_rr_n registers to their stage minimax centres (reach $ot_rr_reach um)"
if {$ot_rr_strict && [regexp {"gt405_after": ([0-9]+)} $ot_rr_log -> ot_rr_left] && $ot_rr_left > 0} {
  error "OT_REACH_RELOC: $ot_rr_left stage endpoint spans > 405 um remain after relocation (structural relay needed)"
}
