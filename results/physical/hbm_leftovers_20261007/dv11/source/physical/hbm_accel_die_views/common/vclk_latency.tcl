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
    # corner-true FF hold on outputs (approved common recipe, stations finding 2026-10-06: one SS figure on the hold
    # side costs ~130 ps of needless hold buffers per output): the FF hold of an output is timed against vclk at the
    # block's FF MINIMUM insertion with a 50 ps IO hold uncertainty.  One SDC serves every scene, so this is an output
    # -min delay of L - Lff_min - 25 (vclk's own hold uncertainty is 25); at the slow scene that only relaxes a check
    # sign-off does not make (hold is signed off at FF).  Inputs keep -min 0 against L in the flow; sign-off times
    # them at the FF maximum insertion (vclk_corner_true.sdc).
    if {![catch {sta::redirect_string_begin; report_clock_latency -clocks core_clk -scenes BC; set sf [sta::redirect_string_end]}] && \
        [regexp {rise -> rise.*?([0-9.]+)\s+([0-9.]+)\s+latency} $sf -> flo fhi]} {
      set d [expr {round($L - $flo - 25)}]
      if {$d > 0} {
        set_output_delay -min $d -clock vclk [all_outputs]
        puts "ot_vclk_from_insertion: FF insertion $flo .. $fhi ps -> output hold vs vclk at FF min: output -min $d ps"
      }
    } else {
      catch {sta::redirect_string_end}
      puts "ot_vclk_from_insertion: no BC scene latency; output hold unchanged"
    }
  } else {
    puts "ot_vclk_from_insertion: no core_clk latency report; vclk unchanged"
  }
}
