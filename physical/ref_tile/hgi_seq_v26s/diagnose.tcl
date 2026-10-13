# Verify rollback operations in the real OpenDB interpreter before building clocks.
foreach ot_seq26_api {odb::dbInst_destroy odb::dbNet_destroy} {
  if {[info commands $ot_seq26_api] eq ""} { error "SEQ26 required rollback API absent: $ot_seq26_api" }
}
puts "SEQ26 OpenDB rollback APIs available"
# Keep the real source/capture clock paths before a long repair can be interrupted.
# This hook changes no clock, path exception, delay or repair setting.
if {[info commands repair_timing] ne "" && [info commands ot_seq26_repair_orig] eq ""} {
  rename repair_timing ot_seq26_repair_orig
  proc repair_timing {args} {
    if {[info exists ::env(REPORTS_DIR)]} {
      set tag [expr {[lsearch -exact $args -hold] >= 0 ? "hold" : "setup"}]
      set out [file join $::env(REPORTS_DIR) seq26_${tag}_before_repair.rpt]
      if {![file exists $out]} {
        if {[catch {report_checks -path_delay [expr {$tag eq "hold" ? "min" : "max"}] -format full_clock_expanded -digits 4 -group_count 20 > $out} e]} {
          puts "SEQ26 diagnostic report unavailable: $e"
        } else { puts "SEQ26 diagnostic saved $out" }
      }
    }
    return [ot_seq26_repair_orig {*}$args]
  }
}
