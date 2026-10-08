# CLAUDE HBM-ABSTRACTS die views: vclk at the view's MEASURED clock insertion (owner rule 2026-10-06: IO constraints
# budget the die clock-arrival difference against the block's measured insertion).  io_vclk_m_<L>.sdc sets a planning
# L for placement (ideal clocks); once CTS has built the tree, ot_vclk_from_insertion sets vclk's latency to the
# midpoint of core_clk's propagated insertion (report_clock_latency, rise) before any timing repair, so every IO path
# sees only its register's skew from the block's own mean insertion (+ the SDC's 150 ps allowance).  The value is
# written into 4_cts.sdc / 6_final.sdc by ORFS (write_sdc) and so reaches sign-off.  post_cts_vclk.tcl re-measures after
# the CTS-stage repair (it moves the insertion: qm2_pd55 517-1029 ps before, 848-1029 ps after).
# CLAUDE S81-PH (2026-10-06 PM): per-corner insertion.  report_clock_latency without -scenes mixes corners (tile_m2:
# min 221 = the BC tree, max 378 = the WC tree -> midpoint 300 ps, ~70 ps under the WC tree), and the same vclk latency
# was used for the BC hold checks of every output: hold repair padded every output by ~185 ps at BC (= ~370 ps of
# BUFx2 chains at WC; tile_m2 co/lt_wo/rso -134..-178 ps setup).  Now:
#   vclk latency           = midpoint of the WC (primary) tree             (input setup/hold launch, output setup capture)
#   output min delay       = L - (BC max insertion + 25 ps)                (with the 25 ps hold uncertainty: the receiver
#                            captures <= 50 ps after our latest BC leaf: the owner's FF insertion + 50 ps hold IO term)
# Input hold is a die-context check (io sdc: set_false_path -hold from the inputs), as in the su_swiglu re-route.
proc ot_clk_ins {scene} {
  sta::redirect_string_begin
  set rc [catch {if {$scene eq ""} { report_clock_latency -clock core_clk } else { report_clock_latency -clock core_clk -scenes $scene }}]
  set s [sta::redirect_string_end]
  if {!$rc && [regexp {rise -> rise.*?([0-9.]+)\s+([0-9.]+)\s+latency} $s -> lo hi]} { return [list $lo $hi] }
  return {}
}
proc ot_vclk_from_insertion {{force 0}} {
  if {(!$force && [info exists ::ot_vclk_L_done]) || [llength [get_clocks -quiet vclk]] == 0} { return }
  set wc [ot_clk_ins WC]; set bc [ot_clk_ins BC]
  if {[llength $wc] == 0} { set wc [ot_clk_ins {}] }
  if {[llength $wc] == 0} { puts "ot_vclk_from_insertion: no core_clk latency report; vclk unchanged"; return }
  lassign $wc lo hi
  set L [expr {round(($lo + $hi) / 2.0)}]
  set_clock_latency $L [get_clocks vclk]
  set ::ot_vclk_L_done $L
  if {[llength $bc]} {
    set omin [expr {$L - round([lindex $bc 1]) - 25}]
    set_output_delay -min $omin -clock vclk [all_outputs]
    puts "ot_vclk_from_insertion: core_clk WC $lo .. $hi, BC $bc ps -> vclk latency $L ps, output min delay $omin ps"
  } else {
    puts "ot_vclk_from_insertion: core_clk $lo .. $hi ps (no per-scene report) -> vclk latency $L ps"
  }
}
