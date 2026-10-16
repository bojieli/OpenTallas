set ::ot_ce_require_wire 1
# OT_CLOCK_ENTRY_DOMAIN_API_VERSION 1
# AUTO clock entries: bound insertion.json boundary refs; no ETM arc modification.
set ::ot_ce_refs [dict create {qfd_su_lane_h_native_crom5/clk} {tt {319.5 332.8 348.2} ff {247.0 258.2 271.9} ss {441.2 462.5 488.8}} {qfd_su_sfu_rcp_native45/clk} {tt {295.3 299.8 311.7} ff {233.4 236.9 244.6} ss {399.6 406.2 425.3}} {qfd_su_sfu_rsq_native45/clk} {tt {331.7 335.5 347.9} ff {262.2 266.0 277.6} ss {448.3 452.0 465.3}} {qfd_su_sfu_exp_native45/clk} {tt {324.5 337.1 357.0} ff {256.5 266.0 286.5} ss {439.4 457.1 475.0}}]
set ::ot_ce_counts [dict create {qfd_su_lane_h_native_crom5} 64 {qfd_su_sfu_rcp_native45} 64 {qfd_su_sfu_rsq_native45} 64 {qfd_su_sfu_exp_native45} 64]
set ::ot_ce_domains [dict create {core} {clock core_clk io_budget_ps 166.667 inputs {{*}} outputs {{*}}}]
set ::ot_ce_source_domains [dict create {ck} {core} {ck_head0} {core} {ck_head1} {core} {ck_head2} {core} {ck_head3} {core} {ck_head4} {core} {ck_head5} {core} {ck_head6} {core} {ck_head7} {core} {ck_head8} {core} {ck_head9} {core} {ck_head10} {core} {ck_head11} {core} {ck_head12} {core} {ck_head13} {core} {ck_head14} {core} {ck_head15} {core} {ck_head16} {core} {ck_head17} {core} {ck_head18} {core} {ck_head19} {core} {ck_head20} {core} {ck_head21} {core} {ck_head22} {core} {ck_head23} {core} {ck_head24} {core} {ck_head25} {core} {ck_head26} {core} {ck_head27} {core} {ck_head28} {core} {ck_head29} {core} {ck_head30} {core} {ck_head31} {core} {ck_head32} {core} {ck_head33} {core} {ck_head34} {core} {ck_head35} {core} {ck_head36} {core} {ck_head37} {core} {ck_head38} {core} {ck_head39} {core} {ck_head40} {core} {ck_head41} {core} {ck_head42} {core} {ck_head43} {core} {ck_head44} {core} {ck_head45} {core} {ck_head46} {core} {ck_head47} {core} {ck_head48} {core} {ck_head49} {core} {ck_head50} {core} {ck_head51} {core} {ck_head52} {core} {ck_head53} {core} {ck_head54} {core} {ck_head55} {core} {ck_head56} {core} {ck_head57} {core} {ck_head58} {core} {ck_head59} {core} {ck_head60} {core} {ck_head61} {core} {ck_head62} {core} {ck_head63} {core} {ck_exp0} {core} {ck_exp1} {core} {ck_exp2} {core} {ck_exp3} {core} {ck_exp4} {core} {ck_exp5} {core} {ck_exp6} {core} {ck_exp7} {core} {ck_exp8} {core} {ck_exp9} {core} {ck_exp10} {core} {ck_exp11} {core} {ck_exp12} {core} {ck_exp13} {core} {ck_exp14} {core} {ck_exp15} {core} {ck_exp16} {core} {ck_exp17} {core} {ck_exp18} {core} {ck_exp19} {core} {ck_exp20} {core} {ck_exp21} {core} {ck_exp22} {core} {ck_exp23} {core} {ck_exp24} {core} {ck_exp25} {core} {ck_exp26} {core} {ck_exp27} {core} {ck_exp28} {core} {ck_exp29} {core} {ck_exp30} {core} {ck_exp31} {core} {ck_exp32} {core} {ck_exp33} {core} {ck_exp34} {core} {ck_exp35} {core} {ck_exp36} {core} {ck_exp37} {core} {ck_exp38} {core} {ck_exp39} {core} {ck_exp40} {core} {ck_exp41} {core} {ck_exp42} {core} {ck_exp43} {core} {ck_exp44} {core} {ck_exp45} {core} {ck_exp46} {core} {ck_exp47} {core} {ck_exp48} {core} {ck_exp49} {core} {ck_exp50} {core} {ck_exp51} {core} {ck_exp52} {core} {ck_exp53} {core} {ck_exp54} {core} {ck_exp55} {core} {ck_exp56} {core} {ck_exp57} {core} {ck_exp58} {core} {ck_exp59} {core} {ck_exp60} {core} {ck_exp61} {core} {ck_exp62} {core} {ck_exp63} {core} {ck_rcp0} {core} {ck_rcp1} {core} {ck_rcp2} {core} {ck_rcp3} {core} {ck_rcp4} {core} {ck_rcp5} {core} {ck_rcp6} {core} {ck_rcp7} {core} {ck_rcp8} {core} {ck_rcp9} {core} {ck_rcp10} {core} {ck_rcp11} {core} {ck_rcp12} {core} {ck_rcp13} {core} {ck_rcp14} {core} {ck_rcp15} {core} {ck_rcp16} {core} {ck_rcp17} {core} {ck_rcp18} {core} {ck_rcp19} {core} {ck_rcp20} {core} {ck_rcp21} {core} {ck_rcp22} {core} {ck_rcp23} {core} {ck_rcp24} {core} {ck_rcp25} {core} {ck_rcp26} {core} {ck_rcp27} {core} {ck_rcp28} {core} {ck_rcp29} {core} {ck_rcp30} {core} {ck_rcp31} {core} {ck_rcp32} {core} {ck_rcp33} {core} {ck_rcp34} {core} {ck_rcp35} {core} {ck_rcp36} {core} {ck_rcp37} {core} {ck_rcp38} {core} {ck_rcp39} {core} {ck_rcp40} {core} {ck_rcp41} {core} {ck_rcp42} {core} {ck_rcp43} {core} {ck_rcp44} {core} {ck_rcp45} {core} {ck_rcp46} {core} {ck_rcp47} {core} {ck_rcp48} {core} {ck_rcp49} {core} {ck_rcp50} {core} {ck_rcp51} {core} {ck_rcp52} {core} {ck_rcp53} {core} {ck_rcp54} {core} {ck_rcp55} {core} {ck_rcp56} {core} {ck_rcp57} {core} {ck_rcp58} {core} {ck_rcp59} {core} {ck_rcp60} {core} {ck_rcp61} {core} {ck_rcp62} {core} {ck_rcp63} {core} {ck_rsq0} {core} {ck_rsq1} {core} {ck_rsq2} {core} {ck_rsq3} {core} {ck_rsq4} {core} {ck_rsq5} {core} {ck_rsq6} {core} {ck_rsq7} {core} {ck_rsq8} {core} {ck_rsq9} {core} {ck_rsq10} {core} {ck_rsq11} {core} {ck_rsq12} {core} {ck_rsq13} {core} {ck_rsq14} {core} {ck_rsq15} {core} {ck_rsq16} {core} {ck_rsq17} {core} {ck_rsq18} {core} {ck_rsq19} {core} {ck_rsq20} {core} {ck_rsq21} {core} {ck_rsq22} {core} {ck_rsq23} {core} {ck_rsq24} {core} {ck_rsq25} {core} {ck_rsq26} {core} {ck_rsq27} {core} {ck_rsq28} {core} {ck_rsq29} {core} {ck_rsq30} {core} {ck_rsq31} {core} {ck_rsq32} {core} {ck_rsq33} {core} {ck_rsq34} {core} {ck_rsq35} {core} {ck_rsq36} {core} {ck_rsq37} {core} {ck_rsq38} {core} {ck_rsq39} {core} {ck_rsq40} {core} {ck_rsq41} {core} {ck_rsq42} {core} {ck_rsq43} {core} {ck_rsq44} {core} {ck_rsq45} {core} {ck_rsq46} {core} {ck_rsq47} {core} {ck_rsq48} {core} {ck_rsq49} {core} {ck_rsq50} {core} {ck_rsq51} {core} {ck_rsq52} {core} {ck_rsq53} {core} {ck_rsq54} {core} {ck_rsq55} {core} {ck_rsq56} {core} {ck_rsq57} {core} {ck_rsq58} {core} {ck_rsq59} {core} {ck_rsq60} {core} {ck_rsq61} {core} {ck_rsq62} {core} {ck_rsq63} {core} {ck_align0} {core} {ck_align1} {core} {ck_align2} {core} {ck_align3} {core} {ck_align4} {core} {ck_align5} {core} {ck_align6} {core} {ck_align7} {core} {ck_align8} {core} {ck_align9} {core} {ck_align10} {core} {ck_align11} {core} {ck_align12} {core} {ck_align13} {core} {ck_align14} {core} {ck_align15} {core} {ck_lane0} {core} {ck_lane1} {core} {ck_lane2} {core} {ck_lane3} {core} {ck_lane4} {core} {ck_lane5} {core} {ck_lane6} {core} {ck_lane7} {core} {ck_lane8} {core} {ck_lane9} {core} {ck_lane10} {core} {ck_lane11} {core} {ck_lane12} {core} {ck_lane13} {core} {ck_lane14} {core} {ck_lane15} {core} {ck_lane16} {core} {ck_lane17} {core} {ck_lane18} {core} {ck_lane19} {core} {ck_lane20} {core} {ck_lane21} {core} {ck_lane22} {core} {ck_lane23} {core} {ck_lane24} {core} {ck_lane25} {core} {ck_lane26} {core} {ck_lane27} {core} {ck_lane28} {core} {ck_lane29} {core} {ck_lane30} {core} {ck_lane31} {core} {ck_lane32} {core} {ck_lane33} {core} {ck_lane34} {core} {ck_lane35} {core} {ck_lane36} {core} {ck_lane37} {core} {ck_lane38} {core} {ck_lane39} {core} {ck_lane40} {core} {ck_lane41} {core} {ck_lane42} {core} {ck_lane43} {core} {ck_lane44} {core} {ck_lane45} {core} {ck_lane46} {core} {ck_lane47} {core} {ck_lane48} {core} {ck_lane49} {core} {ck_lane50} {core} {ck_lane51} {core} {ck_lane52} {core} {ck_lane53} {core} {ck_lane54} {core} {ck_lane55} {core} {ck_lane56} {core} {ck_lane57} {core} {ck_lane58} {core} {ck_lane59} {core} {ck_lane60} {core} {ck_lane61} {core} {ck_lane62} {core} {ck_lane63} {core} {ck_red0} {core} {ck_red1} {core} {ck_red2} {core} {ck_red3} {core} {ck_red4} {core} {ck_red5} {core} {ck_red6} {core} {ck_red7} {core} {ck_red8} {core}]
set ::ot_ce_explicit_domains 0
set ::ot_ce_cts_roots {{ck} {ck_lane0} {ck_lane1} {ck_lane2} {ck_lane3} {ck_lane4} {ck_lane5} {ck_lane6} {ck_lane7} {ck_lane8} {ck_lane9} {ck_lane10} {ck_lane11} {ck_lane12} {ck_lane13} {ck_lane14} {ck_lane15} {ck_lane16} {ck_lane17} {ck_lane18} {ck_lane19} {ck_lane20} {ck_lane21} {ck_lane22} {ck_lane23} {ck_lane24} {ck_lane25} {ck_lane26} {ck_lane27} {ck_lane28} {ck_lane29} {ck_lane30} {ck_lane31} {ck_lane32} {ck_lane33} {ck_lane34} {ck_lane35} {ck_lane36} {ck_lane37} {ck_lane38} {ck_lane39} {ck_lane40} {ck_lane41} {ck_lane42} {ck_lane43} {ck_lane44} {ck_lane45} {ck_lane46} {ck_lane47} {ck_lane48} {ck_lane49} {ck_lane50} {ck_lane51} {ck_lane52} {ck_lane53} {ck_lane54} {ck_lane55} {ck_lane56} {ck_lane57} {ck_lane58} {ck_lane59} {ck_lane60} {ck_lane61} {ck_lane62} {ck_lane63} {ck_align0} {ck_align1} {ck_align2} {ck_align3} {ck_align4} {ck_align5} {ck_align6} {ck_align7} {ck_align8} {ck_align9} {ck_align10} {ck_align11} {ck_align12} {ck_align13} {ck_align14} {ck_align15} {ck_red0} {ck_red1} {ck_red2} {ck_red3} {ck_red4} {ck_red5} {ck_red6} {ck_red7} {ck_red8}}
set ::ot_ce_ports {{ck} {ck_head0} {ck_head1} {ck_head2} {ck_head3} {ck_head4} {ck_head5} {ck_head6} {ck_head7} {ck_head8} {ck_head9} {ck_head10} {ck_head11} {ck_head12} {ck_head13} {ck_head14} {ck_head15} {ck_head16} {ck_head17} {ck_head18} {ck_head19} {ck_head20} {ck_head21} {ck_head22} {ck_head23} {ck_head24} {ck_head25} {ck_head26} {ck_head27} {ck_head28} {ck_head29} {ck_head30} {ck_head31} {ck_head32} {ck_head33} {ck_head34} {ck_head35} {ck_head36} {ck_head37} {ck_head38} {ck_head39} {ck_head40} {ck_head41} {ck_head42} {ck_head43} {ck_head44} {ck_head45} {ck_head46} {ck_head47} {ck_head48} {ck_head49} {ck_head50} {ck_head51} {ck_head52} {ck_head53} {ck_head54} {ck_head55} {ck_head56} {ck_head57} {ck_head58} {ck_head59} {ck_head60} {ck_head61} {ck_head62} {ck_head63} {ck_exp0} {ck_exp1} {ck_exp2} {ck_exp3} {ck_exp4} {ck_exp5} {ck_exp6} {ck_exp7} {ck_exp8} {ck_exp9} {ck_exp10} {ck_exp11} {ck_exp12} {ck_exp13} {ck_exp14} {ck_exp15} {ck_exp16} {ck_exp17} {ck_exp18} {ck_exp19} {ck_exp20} {ck_exp21} {ck_exp22} {ck_exp23} {ck_exp24} {ck_exp25} {ck_exp26} {ck_exp27} {ck_exp28} {ck_exp29} {ck_exp30} {ck_exp31} {ck_exp32} {ck_exp33} {ck_exp34} {ck_exp35} {ck_exp36} {ck_exp37} {ck_exp38} {ck_exp39} {ck_exp40} {ck_exp41} {ck_exp42} {ck_exp43} {ck_exp44} {ck_exp45} {ck_exp46} {ck_exp47} {ck_exp48} {ck_exp49} {ck_exp50} {ck_exp51} {ck_exp52} {ck_exp53} {ck_exp54} {ck_exp55} {ck_exp56} {ck_exp57} {ck_exp58} {ck_exp59} {ck_exp60} {ck_exp61} {ck_exp62} {ck_exp63} {ck_rcp0} {ck_rcp1} {ck_rcp2} {ck_rcp3} {ck_rcp4} {ck_rcp5} {ck_rcp6} {ck_rcp7} {ck_rcp8} {ck_rcp9} {ck_rcp10} {ck_rcp11} {ck_rcp12} {ck_rcp13} {ck_rcp14} {ck_rcp15} {ck_rcp16} {ck_rcp17} {ck_rcp18} {ck_rcp19} {ck_rcp20} {ck_rcp21} {ck_rcp22} {ck_rcp23} {ck_rcp24} {ck_rcp25} {ck_rcp26} {ck_rcp27} {ck_rcp28} {ck_rcp29} {ck_rcp30} {ck_rcp31} {ck_rcp32} {ck_rcp33} {ck_rcp34} {ck_rcp35} {ck_rcp36} {ck_rcp37} {ck_rcp38} {ck_rcp39} {ck_rcp40} {ck_rcp41} {ck_rcp42} {ck_rcp43} {ck_rcp44} {ck_rcp45} {ck_rcp46} {ck_rcp47} {ck_rcp48} {ck_rcp49} {ck_rcp50} {ck_rcp51} {ck_rcp52} {ck_rcp53} {ck_rcp54} {ck_rcp55} {ck_rcp56} {ck_rcp57} {ck_rcp58} {ck_rcp59} {ck_rcp60} {ck_rcp61} {ck_rcp62} {ck_rcp63} {ck_rsq0} {ck_rsq1} {ck_rsq2} {ck_rsq3} {ck_rsq4} {ck_rsq5} {ck_rsq6} {ck_rsq7} {ck_rsq8} {ck_rsq9} {ck_rsq10} {ck_rsq11} {ck_rsq12} {ck_rsq13} {ck_rsq14} {ck_rsq15} {ck_rsq16} {ck_rsq17} {ck_rsq18} {ck_rsq19} {ck_rsq20} {ck_rsq21} {ck_rsq22} {ck_rsq23} {ck_rsq24} {ck_rsq25} {ck_rsq26} {ck_rsq27} {ck_rsq28} {ck_rsq29} {ck_rsq30} {ck_rsq31} {ck_rsq32} {ck_rsq33} {ck_rsq34} {ck_rsq35} {ck_rsq36} {ck_rsq37} {ck_rsq38} {ck_rsq39} {ck_rsq40} {ck_rsq41} {ck_rsq42} {ck_rsq43} {ck_rsq44} {ck_rsq45} {ck_rsq46} {ck_rsq47} {ck_rsq48} {ck_rsq49} {ck_rsq50} {ck_rsq51} {ck_rsq52} {ck_rsq53} {ck_rsq54} {ck_rsq55} {ck_rsq56} {ck_rsq57} {ck_rsq58} {ck_rsq59} {ck_rsq60} {ck_rsq61} {ck_rsq62} {ck_rsq63} {ck_align0} {ck_align1} {ck_align2} {ck_align3} {ck_align4} {ck_align5} {ck_align6} {ck_align7} {ck_align8} {ck_align9} {ck_align10} {ck_align11} {ck_align12} {ck_align13} {ck_align14} {ck_align15} {ck_lane0} {ck_lane1} {ck_lane2} {ck_lane3} {ck_lane4} {ck_lane5} {ck_lane6} {ck_lane7} {ck_lane8} {ck_lane9} {ck_lane10} {ck_lane11} {ck_lane12} {ck_lane13} {ck_lane14} {ck_lane15} {ck_lane16} {ck_lane17} {ck_lane18} {ck_lane19} {ck_lane20} {ck_lane21} {ck_lane22} {ck_lane23} {ck_lane24} {ck_lane25} {ck_lane26} {ck_lane27} {ck_lane28} {ck_lane29} {ck_lane30} {ck_lane31} {ck_lane32} {ck_lane33} {ck_lane34} {ck_lane35} {ck_lane36} {ck_lane37} {ck_lane38} {ck_lane39} {ck_lane40} {ck_lane41} {ck_lane42} {ck_lane43} {ck_lane44} {ck_lane45} {ck_lane46} {ck_lane47} {ck_lane48} {ck_lane49} {ck_lane50} {ck_lane51} {ck_lane52} {ck_lane53} {ck_lane54} {ck_lane55} {ck_lane56} {ck_lane57} {ck_lane58} {ck_lane59} {ck_lane60} {ck_lane61} {ck_lane62} {ck_lane63} {ck_red0} {ck_red1} {ck_red2} {ck_red3} {ck_red4} {ck_red5} {ck_red6} {ck_red7} {ck_red8}}

proc ot_ce_corner {} {
  if {[info exists ::ot_ioref_scene] && $::ot_ioref_scene eq "BC"} { return ff }
  if {[info exists ::ot_ce_corner]} { return $::ot_ce_corner }
  # WC is a scene label, not an actual library corner: option-B overlays WC
  # with TT. Bind the reference to actual loaded child Liberty objects.
  set found {}
  foreach cell [get_cells -quiet -hierarchical *] {
    set master [get_property $cell ref_name]
    if {![dict exists $::ot_ce_counts $master]} continue
    set libcells [get_lib_cells -quiet -of_objects $cell]
    if {![llength $libcells]} { error "OT_ENTRIES: $master has no loaded Liberty association" }
    foreach lc $libcells {
      set full [get_full_name $lc]
      if {![regexp -nocase {_(tt|ff|ss)/} $full -> corner]} { error "OT_ENTRIES: unknown actual child Liberty corner $full" }
      dict set found [string tolower $corner] 1
    }
  }
  if {[dict size $found] == 1} { return [lindex [dict keys $found] 0] }
  # A multi-mode database needs its actual setup corner or BC scene shim.
  if {[info exists ::env(OT_MM_SETUP_CORNER)]} {
    switch -nocase -- $::env(OT_MM_SETUP_CORNER) {
      TC - tt {set corner tt} BC - ff {set corner ff} WC - ss {set corner ss}
      default { error "OT_ENTRIES: unknown actual setup corner" }
    }
    if {[dict exists $found $corner]} { return $corner }
  }
  error "OT_ENTRIES: ambiguous actual loaded child corners [dict keys $found]"
}
# get_property pin arrival_max_rise is a DATA arrival query. On a clock-only
# macro pin it returns an infinity sentinel even with a finite propagated clock
# path. Read propagated clock tags in the current scene and remove the
# source waveform edge time; falling-edge-only registers include that phase.
proc ot_ce_finite {value} {
  return [expr {[string is double -strict $value] && ![regexp -nocase {inf|nan} $value]}]
}
proc ot_ce_clock_wire {pin clock} {
  set scene [get_property [sta::cmd_scene] name]
  set clock_name [get_full_name $clock]
  set by_transition [dict create rise {} fall {}]
  set waveform {}
  foreach time [$clock waveform] {lappend waveform [sta::time_sta_ui $time]}
  if {[llength $waveform] != 2 || ![ot_ce_finite [lindex $waveform 0]] ||
      ![ot_ce_finite [lindex $waveform 1]]} {
    error "OT_ENTRIES: invalid source clock waveform $clock_name"
  }
  foreach vertex [$pin vertices] {
    if {$vertex eq "NULL"} continue
    foreach transition {rise fall} marker {^ v} {
      set paths [$vertex path_iterator $transition max]
      while {[$paths has_next]} {
        set path [$paths next]
        # Sink transition and source clock edge are distinct (inverting trees).
        # Exclude data, ideal, other-scene and other-clock paths as before.
        set tag [$path tag]
        set edge [lindex $tag 4]
        if {[lindex $tag 1] ne $scene || [lindex $tag 2] ne "${marker}max" ||
            [lindex $tag 3] ne $clock_name || $edge ni {^ v} ||
            [string first "(clock prop)" $tag] < 0} continue
        set arrival [sta::time_sta_ui [$path arrival]]
        if {![ot_ce_finite $arrival]} {
          $paths finish
          error "OT_ENTRIES: nonfinite propagated clock arrival on [get_full_name $pin] scene=$scene clock=$clock_name"
        }
        set phase [lindex $waveform [expr {$edge eq "^" ? 0 : 1}]]
        dict lappend by_transition $transition [expr {$arrival - $phase}]
      }
      $paths finish
    }
  }
  # Preserve the rising pin-transition reference. An inverted/negedge clock
  # may associate it with the falling source edge; remove that actual phase.
  # Fall-only pins remain measurable. Multiple same-transition tags fail.
  set values [dict get $by_transition rise]
  if {![llength $values]} {set values [dict get $by_transition fall]}
  if {[llength $values] != 1} {
    # Synthesis/floorplan have no extracted entry wire. This is solely a finite
    # pre-CTS diagnostic reference; routed gates must measure a clock path.
    if {![llength $values] && [info exists ::ot_ref_pre_cts] && $::ot_ref_pre_cts &&
        (![info exists ::ot_ce_require_wire] || !$::ot_ce_require_wire)} {
      puts "OT_ENTRIES PRE_CTS_ZERO_WIRE [get_full_name $pin] scene=$scene"
      return 0.0
    }
    error "OT_ENTRIES: missing unique finite propagated clock arrival on [get_full_name $pin] scene=$scene clock=$clock_name"
  }
  return [lindex $values 0]
}
# Match ck_insertion.py's exported insertion.json boundary population: input
# timing endpoints plus output timing launch registers, intersected with this root.
proc ot_ce_boundary_cells {} {
  set boundary {}
  set inputs [all_inputs -no_clocks]
  if {[llength $inputs]} {
    foreach path [find_timing_paths -path_delay max -from $inputs -to [all_registers -data_pins] -group_path_count 200000 -endpoint_path_count 1] {
      dict set boundary [regsub {/[^/]+$} [get_full_name [get_property $path endpoint]] {}] 1
    }
  }
  if {[llength [all_outputs]]} {
    foreach path [find_timing_paths -path_delay max -from [all_registers -clock_pins] -to [all_outputs] -group_path_count 200000 -endpoint_path_count 100000] {
      dict set boundary [regsub {/[^/]+$} [get_full_name [get_property $path startpoint]] {}] 1
    }
  }
  return $boundary
}
proc ot_ce_boundary_pins {pins boundary_cells} {
  set regs {}; set boundary {}
  foreach pin $pins {dict set regs [regsub {/[^/]+$} [get_full_name $pin] {}] $pin}
  dict for {name unused} $boundary_cells {
    if {[dict exists $regs $name]} {dict set boundary $name [dict get $regs $name]}
  }
  return [dict values $boundary]
}

proc ot_ce_apply {} {
  set corner [ot_ce_corner]
  set clk [get_clocks core_clk]
  if {[llength $clk] != 1} { error "OT_ENTRIES: core_clk missing" }
  # Wires-only parents have no CTS tree to set this flag for us.
  # Ideal clocks silently report zero network arrival despite real entry wires.
  set_propagated_clock [get_clocks ot_entry_*]
  # Before CTS, a standard-cell root is still one unbuffered high-fanout
  # net. Propagating that net invents multi-ns skew and clock-pin slew;
  # its delay is not the tree that CTS will build. Keep only these declared
  # CTS roots ideal during the explicit pre-CTS diagnostic. Raw macro and
  # hardened-child entries retain actual entry-wire propagation. Routed
  # require-wire checks always propagate and measure every physical root.
  if {[info exists ::ot_ref_pre_cts] && $::ot_ref_pre_cts &&
      (![info exists ::ot_ce_require_wire] || !$::ot_ce_require_wire)} {
    foreach name $::ot_ce_cts_roots {
      set clock [get_clocks ot_entry_[lsearch -exact $::ot_ce_ports $name]]
      unset_propagated_clock $clock
      puts "OT_ENTRIES PRE_CTS_IDEAL_CTS_ROOT $name"
    }
  }
  set sources {}; set names {}
  foreach c [get_clocks ot_entry_*] {
    foreach p [get_property $c sources] { lappend sources $p; lappend names [get_full_name $p] }
  }
  if {[lsort $names] ne [lsort $::ot_ce_ports]} { error "OT_ENTRIES: source clock coverage differs from spec" }
  foreach c [get_clocks ot_entry_*] { set_clock_latency -source 0 $c }
  sta::worst_slack_cmd max
  set rows {}; set seen {}; set counts {}
  foreach cell [get_cells -quiet -hierarchical *] {
    set master [get_property $cell ref_name]
    if {![dict exists $::ot_ce_counts $master]} continue
    dict incr counts $master
    foreach pin [get_pins -quiet -of_objects $cell] {
      set key "$master/[get_property $pin lib_pin_name]"
      if {![dict exists $::ot_ce_refs $key]} continue
      set ports [get_ports -quiet -of_objects [get_nets -quiet -of_objects $pin]]
      if {[llength $ports] != 1} { error "OT_ENTRIES: [get_full_name $pin] lacks one direct top clock port" }
      set port [lindex $ports 0]; set name [get_full_name $port]
      if {$name ni $::ot_ce_ports || $name in $::ot_ce_cts_roots || [dict exists $seen $name]} { error "OT_ENTRIES: duplicate or undeclared source $name" }
      dict set seen $name 1
      set clock [get_clocks ot_entry_[lsearch -exact $::ot_ce_ports $name]]
      if {[llength $clock] != 1} { error "OT_ENTRIES: $name has no unique related clock" }
      set wire [ot_ce_clock_wire $pin $clock]
      if {![ot_ce_finite $wire]} { error "OT_ENTRIES: nonfinite entry wire clock arrival on [get_full_name $pin]" }
      if {abs($wire) < 1.0e-9 && [info exists ::ot_ce_require_wire] && $::ot_ce_require_wire} {
        # A zero arrival is admissible only if actual source and child pin are
        # physically coincident. Missing parasitics/ideal clocks cannot qualify.
        if {![llength [info commands ord::get_db_block]]} { error "OT_ENTRIES: zero wire lacks physical source/pin proof" }
        set block [ord::get_db_block]
        set bt [$block findBTerm $name]
        set it [$block findITerm [get_full_name $pin]]
        if {$bt eq "NULL" || $it eq "NULL"} { error "OT_ENTRIES: missing physical source/child clock pin" }
        set pb [$bt getBBox]; set ib [$it getBBox]
        set distance [expr {(abs(([$pb xMin]+[$pb xMax])-([$ib xMin]+[$ib xMax])) + abs(([$pb yMin]+[$pb yMax])-([$ib yMin]+[$ib yMax]))) / 2.0 / [$block getDbUnitsPerMicron]}]
        if {$distance > 0.001} { error "OT_ENTRIES: zero clock wire arrival despite $distance um source/pin separation on $name" }
        puts "OT_ENTRIES ZERO_WIRE_PROVEN $name [get_full_name $pin] distance=$distance"
      }
      lassign [dict get $::ot_ce_refs $key $corner] lo mean hi
      set clock [get_clocks ot_entry_[lsearch -exact $::ot_ce_ports $name]]
      if {[llength $clock] != 1} { error "OT_ENTRIES: $name has no unique related clock" }
      set ttmean [lindex [dict get $::ot_ce_refs $key tt] 1]
      set domain [dict get $::ot_ce_source_domains $name]
      set vc [get_clocks [dict get $::ot_ce_domains $domain clock]]
      if {abs([get_property $vc period]-[get_property $clock period])>0.001} { error "OT_ENTRIES: domain/source period mismatch $name" }
      lappend rows [list $port $pin $wire $lo $mean $hi $clock $ttmean $domain]
    }
  }
  dict for {m n} $::ot_ce_counts {
    if {![dict exists $counts $m] || [dict get $counts $m] != $n} { error "OT_ENTRIES: bound child count mismatch $m" }
  }
  # Source latencies are zero for this whole measurement loop, and no STA
  # constraints/netlist change until rows are complete. Query the same bounded
  # boundary population once per apply/current corner, never across calls.
  set boundary_cells {}; set boundary_cells_ready 0
  # Each glue root owns a real CTS tree. Measure every propagated standard-cell
  # clock sink in the current scene; never substitute a declared/common phase.
  foreach name $::ot_ce_cts_roots {
    set clock [get_clocks ot_entry_[lsearch -exact $::ot_ce_ports $name]]
    set pins [all_registers -clock [get_full_name $clock] -clock_pins]
    if {![llength $pins]} { error "OT_HYBRID: glue root $name has no actual sequential clock sinks" }
    set arrivals {}; set measured {}; set total 0.0
    foreach pin $pins {
      set cell [get_cells -of_objects $pin]
      set master [get_property $cell ref_name]
      if {[dict exists $::ot_ce_counts $master]} { error "OT_HYBRID: CTS root $name reaches a hard child" }
      set arrival [ot_ce_clock_wire $pin $clock]
      lappend arrivals $arrival
      dict set measured [get_full_name $pin] $arrival
      set total [expr {$total + $arrival}]
    }
    set arrivals [lsort -real $arrivals]
    set lo [lindex $arrivals 0]; set hi [lindex $arrivals end]
    set tree_mean [expr {$total / [llength $arrivals]}]
    set mean $tree_mean
    if {[info exists ::ot_ce_require_wire] && $::ot_ce_require_wire && $mean <= 0} {
      error "OT_HYBRID: glue root $name lacks a positive actual propagated CTS insertion"
    }
    if {[llength $arrivals] > 15000 && ($tree_mean > 300 || $hi-$lo > 80)} {
      error "OT_HYBRID: glue root $name exceeds measured large-root insertion/spread limits"
    }
    if {!$boundary_cells_ready} {
      set boundary_cells [ot_ce_boundary_cells]; set boundary_cells_ready 1
    }
    set boundary [ot_ce_boundary_pins $pins $boundary_cells]
    set scope boundary
    if {![llength $boundary]} { set boundary $pins; set scope all_internal_only }
    set arrivals {}; set total 0.0
    foreach pin $boundary {
      set arrival [dict get $measured [get_full_name $pin]]
      lappend arrivals $arrival; set total [expr {$total + $arrival}]
    }
    set arrivals [lsort -real $arrivals]
    set lo [lindex $arrivals 0]; set hi [lindex $arrivals end]
    set mean [expr {$total / [llength $arrivals]}]
    if {[llength $pins] > 15000 && $mean > 300} {
      error "OT_HYBRID: glue root $name exceeds boundary insertion limit"
    }
    set domain [dict get $::ot_ce_source_domains $name]
    lappend rows [list [get_ports $name] [lindex $pins 0] 0 $lo $mean $hi $clock $mean $domain]
    dict set seen $name 1
    puts "OT_HYBRID CTS_MEASURE $corner $name sinks=[llength $pins] reference_scope=$scope boundary_sinks=[llength $boundary] min=$lo mean=$mean max=$hi all_mean=$tree_mean"
  }
  if {[dict size $seen] != [llength $::ot_ce_ports]} { error "OT_ENTRIES: incomplete actual child/source coverage" }
  set ref 0
  foreach row $rows { lassign $row p pin wire lo mean hi; set ref [expr {max($ref, $wire + $mean)}] }
  set low {}; set high {}; set lowclocks {}; set highclocks {}; set domain_low {}; set domain_high {}
  foreach row $rows {
    lassign $row p pin wire lo mean hi clock ttmean domain
    # Physical source level includes the entry wire, not just the hard
    # child's internal insertion. Only a TT scene measures the TT wire.
    # Other physical scenes conservatively reserve the deep pair budget;
    # they must not guess TT wire delay from FF/SS or an ideal zero arrival.
    set deep [expr {$ttmean > 300}]
    set level_basis "zero-wire diagnostic"
    if {$corner eq "tt"} {
      set deep [expr {$ttmean + $wire > 300}]
      set level_basis "TT timing-graph entry arrival + child R (physical proof required for route/signoff)"
    } elseif {[info exists ::ot_ce_require_wire] && $::ot_ce_require_wire} {
      set deep 1
      set level_basis "TT wire level not measured in this scene; conservative210ps setup"
    }
    if {$deep} { lappend highclocks $clock } else { lappend lowclocks $clock }
    puts "OT_ENTRIES LEVEL [get_full_name $p] deep=$deep basis=$level_basis"
    set latency [expr {$ref - $wire - $mean}]
    if {![ot_ce_finite $ref] || ![ot_ce_finite $latency]} { error "OT_ENTRIES: nonfinite reference/source latency on [get_full_name $p]" }
    set_clock_latency -source $latency $clock
    lappend low [expr {$ref + $lo - $mean}]; lappend high [expr {$ref + $hi - $mean}]
    dict lappend domain_low $domain [expr {$ref + $lo - $mean}]
    dict lappend domain_high $domain [expr {$ref + $hi - $mean}]
    puts "OT_ENTRIES COMP $corner [get_full_name $p] -> [get_full_name $pin] wire=$wire R=$mean latency=$latency phi=$ref"
  }
  # Every entry is synchronous and related. Reserve die skew on internal hops;
  # no asynchronous groups, false paths or ETM insertion add-back.
  # H1 authoritative pair_check.HOLD_TREE =50ps hold margin+50ps die skew (hold 100, setup 150).
  # Each deep tile has its own earlier trunk tap. The authoritative TREE
  # pair budget uses150ps die skew when either reference exceeds300ps,
  # including deep-to-deep pairs (pair_check.SKEW_DEEP) (setup 210).
  # S-ELEM-PQ 2026-10-15: a register pair on ONE glue CTS root of this tile shares one die tap and one
  # propagated standard-cell tree whose real skew STA already sees, so it is timed like every single-root
  # tile (base uncertainty); the die-skew reserve applies to every pair of DIFFERENT entries and to hard-
  # child entries (dsfd_bf_front_static: the uniform rule put hold 100 / setup 210 on all 12,276 core-root
  # paths -> 15,826 hold endpoints, 119k buffers).
  set ot_ce_glue {}
  foreach name $::ot_ce_cts_roots { lappend ot_ce_glue [get_full_name [get_clocks ot_entry_[lsearch -exact $::ot_ce_ports $name]]] }
  set ot_ce_high {}
  foreach c $highclocks { lappend ot_ce_high [get_full_name $c] }
  foreach a [get_clocks ot_entry_*] {
    foreach b [get_clocks ot_entry_*] {
      set an [get_full_name $a]; set bn [get_full_name $b]
      if {$an eq $bn && $an in $ot_ce_glue} { continue }
      set_clock_uncertainty -setup [expr {($an in $ot_ce_high || $bn in $ot_ce_high) ? 210 : 150}] -from $a -to $b
      set_clock_uncertainty -hold 100 -from $a -to $b
    }
  }
  # Preserve measured boundary spread: balancing the mean does not erase the
  # earliest/latest physical boundary arrivals or change ETM setup/hold arcs.
  set lmin [lindex [lsort -real $low] 0]; set lmax [lindex [lsort -real $high] end]
  unset_input_delay [all_inputs]; unset_output_delay [all_outputs]
  set sk [expr {[info exists ::env(OT_IO_SKEW)] ? $::env(OT_IO_SKEW) : 90}]
  set hk [expr {[info exists ::env(OT_IO_HOLD_SKEW)] ? $::env(OT_IO_HOLD_SKEW) : 50}]
  set hki [expr {[info exists ::env(OT_IO_IN_HOLD_SKEW)] ? $::env(OT_IO_IN_HOLD_SKEW) : 0}]
  set covered_in {}; set covered_out {}
  dict for {domain info} $::ot_ce_domains {
    if {![dict exists $domain_low $domain]} { error "OT_ENTRIES: domain $domain has no actual child clock pins" }
    set dlmin [lindex [lsort -real [dict get $domain_low $domain]] 0]
    set dlmax [lindex [lsort -real [dict get $domain_high $domain]] end]
    set vc [get_clocks [dict get $info clock]]
    set budget [dict get $info io_budget_ps]
    # Optional composition-derived output budget (domain "io_budget": {"out": f}, f >= 0.2): the outside share of the
    # cycle on this domain's outputs; larger = a TIGHTER launch (flop -> pin) inside the child, never a relaxation.
    set budget_out [expr {[dict exists $info io_budget_out_ps] ? [dict get $info io_budget_out_ps] : $budget}]
    set inputs {}; set outputs {}
    foreach pattern [dict get $info inputs] {
      foreach p [get_ports -quiet $pattern -filter "direction == input"] {
        set n [get_full_name $p]
        if {$n in $::ot_ce_ports} continue
        if {[dict exists $covered_in $n]} { error "OT_ENTRIES: input $n has duplicate IO domains" }
        dict set covered_in $n $domain; lappend inputs $p
      }
    }
    foreach pattern [dict get $info outputs] {
      foreach p [get_ports -quiet $pattern -filter "direction == output"] {
        set n [get_full_name $p]
        if {[dict exists $covered_out $n]} { error "OT_ENTRIES: output $n has duplicate IO domains" }
        dict set covered_out $n $domain; lappend outputs $p
      }
    }
    if {[llength $inputs]} {
      set_input_delay [expr {$budget+$dlmax+$sk}] -max -clock $vc $inputs
      set_input_delay [expr {$dlmin-$hki}] -min -clock $vc $inputs
    }
    if {[llength $outputs]} {
      set_output_delay [expr {$budget_out-$dlmax+$sk}] -max -clock $vc $outputs
      set_output_delay [expr {-$dlmin-$hk}] -min -clock $vc $outputs
    }
    if {[info exists ::env(OT_IO_INTER)] && $::env(OT_IO_INTER) ne ""} {
      foreach pattern [split $::env(OT_IO_INTER) ","] {
        foreach p [get_ports -quiet $pattern] {
          set n [get_full_name $p]
          if {[dict exists $covered_in $n] && [dict get $covered_in $n] eq $domain} {
            set_input_delay [expr {$budget+$dlmax+150}] -max -clock $vc $p
          }
          if {[dict exists $covered_out $n] && [dict get $covered_out $n] eq $domain} {
            set_output_delay [expr {$budget_out-$dlmax+150}] -max -clock $vc $p
          }
        }
      }
    }
    puts "OT_ENTRIES DOMAIN $domain [get_property $vc period]ps IO[llength $inputs]/[llength $outputs] boundary=$dlmin..$dlmax"
  }
  if {[dict size $covered_in] != [llength [all_inputs -no_clocks]] || [dict size $covered_out] != [llength [all_outputs]]} {
    error "OT_ENTRIES: incomplete actual IO domain coverage (resets must also have a domain)"
  }
  puts "OT_ENTRIES COMP DONE $corner [llength $rows] entries phi=$ref boundary=$lmin..$lmax"
}
ot_ce_apply
