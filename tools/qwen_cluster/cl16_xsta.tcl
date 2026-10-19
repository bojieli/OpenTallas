# Q-CL16-EARLY: time every region-to-region crossing of qfd_c_b16_dv (16 regional clocks) at one corner.
# env: OT_C (TT|FF), OT_DB, OT_SDC, OT_PAIRS (file: "launch_clock capture_clock" per line), OT_OUT
set C $::env(OT_C)
set PLAT /OpenROAD-flow-scripts/flow/platforms/asap7
foreach l [glob $PLAT/lib/NLDM/*RVT_${C}*] { read_liberty $l }
foreach l [glob $PLAT/lib/NLDM/*_LVT_${C}_* $PLAT/lib/NLDM/*_SLVT_${C}_*] { if {![string match *FAKE* $l]} { read_liberty $l } }
set c [string tolower $C]
foreach l [glob /src/physical/ref_tile/qfd_c_b16_dv_diag/*_standin/*/*_${c}.lib] { read_liberty $l }
read_db /base/$::env(OT_DB)
read_sdc /base/$::env(OT_SDC)
if {[info exists ::env(OT_SPEF)]} { read_spef $::env(OT_SPEF) } else { source $PLAT/setRC.tcl; estimate_parasitics -placement }
set_propagated_clock [all_clocks]
foreach k [all_clocks] { if {[llength [get_property $k sources]]} { set_clock_latency -source 0 $k } }
set f [open $::env(OT_OUT) w]
set pf [open $::env(OT_PAIRS)]
foreach line [split [read $pf] "\n"] {
  if {[llength $line] != 2} continue
  lassign $line A B
  foreach dly {max min} {
    set pes [find_timing_paths -path_delay $dly -from [get_clocks $A] -to [get_clocks $B] -group_path_count 200000 -endpoint_path_count 1 -unique_paths_to_endpoint]
    foreach pe $pes {
      set ep [get_full_name [get_property $pe endpoint]]
      set sp [get_full_name [get_property $pe startpoint]]
      set sl [get_property $pe slack]
      # clock arrivals: first data-path point = launch clock pin; capture = endpoint instance clock pin via path report
      set pts [get_property $pe points]
      set la [get_property [lindex $pts 0] arrival]
      puts $f "P $dly $A $B $sl $la $sp $ep"
    }
  }
}
close $pf
# full_clock detail of the worst setup / hold path per capture instance (crossing-level skew)
if {[info exists ::env(OT_DETAIL)]} {
  set df [open $::env(OT_DETAIL)]
  foreach line [split [read $df] "\n"] {
    if {[llength $line] != 3} continue
    lassign $line A B pin
    foreach dly {max min} {
      sta::redirect_string_begin
      catch {report_checks -path_delay $dly -from [get_clocks $A] -to [get_pins $pin] -format full_clock -digits 1}
      set r [sta::redirect_string_end]
      puts $f "D_BEGIN $dly $A $B $pin"
      puts $f $r
      puts $f "D_END"
    }
  }
  close $df
}
close $f
exit
