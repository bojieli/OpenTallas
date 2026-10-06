# CLAUDE HBM-ABSTRACTS die views: vclk at the view's MEASURED clock insertion (owner rule 2026-10-06: IO constraints
# budget the die clock-arrival difference against the block's measured insertion).  io_vclk_m_<L>.sdc sets a planning
# L for placement (ideal clocks); once CTS has built the tree, ot_vclk_from_insertion sets vclk's latency to the
# midpoint of core_clk's propagated insertion (report_clock_latency, rise) before any timing repair, so every IO path
# sees only its register's skew from the block's own mean insertion (+ the SDC's 150 ps allowance).  The value is
# written into 4_cts.sdc / 6_final.sdc by ORFS (write_sdc) and so reaches sign-off.  post_cts_vclk.tcl re-measures after
# the CTS-stage repair (it moves the insertion: qm2_pd55 517-1029 ps before, 848-1029 ps after).
proc ot_vclk_from_insertion {{force 0}} {
  if {(!$force && [info exists ::ot_vclk_L_done]) || [llength [get_clocks -quiet vclk]] == 0} { return }
  sta::redirect_string_begin
  report_clock_latency -clock core_clk
  set s [sta::redirect_string_end]
  if {[regexp {rise -> rise.*?([0-9.]+)\s+([0-9.]+)\s+latency} $s -> lo hi]} {
    set L [expr {round(($lo + $hi) / 2.0)}]
    set_clock_latency $L [get_clocks vclk]
    puts "ot_vclk_from_insertion: core_clk insertion $lo .. $hi ps -> vclk latency $L ps"
    set ::ot_vclk_L_done $L
  } else {
    puts "ot_vclk_from_insertion: no core_clk latency report; vclk unchanged"
  }
}
