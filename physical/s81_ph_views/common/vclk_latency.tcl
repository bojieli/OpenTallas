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
proc ot_clk_ins {scene {clk core_clk}} {
  sta::redirect_string_begin
  set rc [catch {if {$scene eq ""} { report_clock_latency -clock $clk } else { report_clock_latency -clock $clk -scenes $scene }}]
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
    # outputs timed against a second virtual clock (vclk_h: the ctrl tiles' PHY ports, hbm_clk domain) keep their own
    # FF model below; a vclk min delay on them would be a bogus hbm_clk -> vclk hold check (ctrl_pc FF -9.7 on k_*)
    set ot_oc {}; set ot_oh {}
    foreach ot_p [all_outputs] {
      set ot_n [get_full_name $ot_p]
      if {[llength [get_clocks -quiet vclk_h]] && [regexp {^(k_v|k_addr|k_len|k_tag|k_we|k_wdata|k_wstrb|kr_rdy|phy_rst_n)(\[|$)} $ot_n]} { lappend ot_oh $ot_p } else { lappend ot_oc $ot_p }
    }
    if {[llength $ot_oc]} { set_output_delay -min $omin -clock vclk $ot_oc }
    if {[llength $ot_oh]} {
      unset_output_delay -clock vclk $ot_oh
      set hw [ot_clk_ins WC hbm_clk]; set hb [ot_clk_ins BC hbm_clk]
      if {[llength $hw] && [llength $hb]} {
        set Lh [expr {round(([lindex $hw 0] + [lindex $hw 1]) / 2.0)}]
        set_clock_latency $Lh [get_clocks vclk_h]
        set_output_delay -min [expr {$Lh - round([lindex $hb 1]) - 25}] -clock vclk_h $ot_oh
        puts "ot_vclk_from_insertion: hbm_clk WC $hw BC $hb -> vclk_h latency $Lh, [llength $ot_oh] PHY outputs min delay [expr {$Lh - round([lindex $hb 1]) - 25}]"
      }
    }
    puts "ot_vclk_from_insertion: core_clk WC $lo .. $hi, BC $bc ps -> vclk latency $L ps, output min delay $omin ps"
  } else {
    puts "ot_vclk_from_insertion: core_clk $lo .. $hi ps (no per-scene report) -> vclk latency $L ps"
  }
}
