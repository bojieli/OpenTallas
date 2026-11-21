# LOCKUP-STATION-1130 (FABLE-CLOSURE-1315 (2)): launch-side lockup latches inserted in the SYNTHESIZED netlist (POST_SYNTH_TCL,
# sourced from face_keep_release.tcl only when gen_phys wrote /work/zl_netlist.txt from plan clock.zl_lockup.<T>.netlist).
# For every register whose flat name matches a line of zl_netlist.txt and whose D net is driven by another register
# through BUF/INV/HB only (a zero-logic hop), one transparent-low DLL latch u_fl_nl_<k> goes
# between them: D <- the launch net, Q -> the capture D, CLK <- the capture's clock net.  clock_taps.tcl hangs every u_fl_*
# on the tap of the flop that drives its D (launch side).  run_kit.sh then proves LEC on the ODB export (1_synth_odb.v,
# lec.py latch_to_wire).  Covers registers the RTL pass cannot edit (generate-block and nested-module registers).
set zn_f /work/zl_netlist.txt
if {![file exists $zn_f]} { return }
# a line "=<name>" is one exact register (station_rule derive --ends-only: the ends that violate hold before repair)
set zn_res {}; set zn_exact [dict create]; set zn_excl {}
foreach l [split [read [set zn_h [open $zn_f]]] "\n"] {
  set l [string trim $l]
  if {$l eq "" || [string match "#*" $l]} continue
  # LOCKUP-STATION-R2: a line "!<re>" excludes the captures whose name matches anywhere (clock.zl_lockup.<T>.auto exclude)
  if {[string index $l 0] eq "="} { dict set zn_exact [string range $l 1 end] 1 } elseif {[string index $l 0] eq "!"} { lappend zn_excl [string range $l 1 end] } else { lappend zn_res $l }
}
close $zn_h
set zn_blk [ord::get_db_block]
set zn_db [ord::get_db]
set zn_m ""
foreach zn_lib [$zn_db getLibs] { foreach zn_c [$zn_lib getMasters] { if {[regexp {^DLLx2_ASAP7_75t_[RLS]} [$zn_c getName]]} { set zn_m $zn_c; break } }; if {$zn_m ne ""} break }
if {$zn_m eq ""} { puts "OT_ZL_NETLIST FAIL no DLLx2 master"; exit 1 }
# rising-edge flops only (DFFL* falling-edge captures / launches keep their own timing; LEC models DFFH)
proc zn_is_reg {m} { return [regexp {^(DFFH|ASYNC_DFFH)} $m] }
set zn_n 0; set zn_skip 0; set zn_k 0
foreach zn_i [$zn_blk getInsts] {
  set zn_nm [string map {\\ {}} [$zn_i getName]]
  if {![zn_is_reg [[$zn_i getMaster] getName]]} continue
  set zn_hit [dict exists $zn_exact $zn_nm]
  if {!$zn_hit} { foreach zn_re $zn_res { if {[regexp -- "^(?:$zn_re)\$" $zn_nm]} { set zn_hit 1; break } } }
  if {!$zn_hit} continue
  foreach zn_re $zn_excl { if {[regexp -- $zn_re $zn_nm]} { set zn_hit 0; break } }
  if {!$zn_hit} { incr zn_skip; continue }
  set zn_d ""; set zn_ck ""
  foreach zn_t [$zn_i getITerms] {
    set zn_p [[$zn_t getMTerm] getName]
    if {$zn_p eq "D"} { set zn_d $zn_t } elseif {$zn_p eq "CLK"} { set zn_ck $zn_t }
  }
  if {$zn_d eq "" || $zn_ck eq "" || [$zn_d getNet] eq "NULL" || [$zn_ck getNet] eq "NULL"} { incr zn_skip; continue }
  set zn_net [$zn_d getNet]
  # back through BUF / INV / HB (a QN-output flop reaches D through one INV) to the launch register, like clock_taps.tcl
  set zn_drv ""; set zn_w $zn_net; set zn_seen {}
  while {$zn_w ne "" && $zn_w ne "NULL" && ![dict exists $zn_seen [$zn_w getName]] && $zn_drv eq ""} {
    dict set zn_seen [$zn_w getName] 1
    set zn_nx ""
    foreach zn_t [$zn_w getITerms] {
      if {[[$zn_t getMTerm] getIoType] ne "OUTPUT"} continue
      set zn_m2 [[[$zn_t getInst] getMaster] getName]
      if {[regexp {^(BUF|INV|HB)} $zn_m2]} {
        foreach zn_in [[$zn_t getInst] getITerms] { if {[[$zn_in getMTerm] getIoType] eq "INPUT" && [$zn_in getNet] ne "NULL"} { set zn_nx [$zn_in getNet] } }
      } elseif {[zn_is_reg $zn_m2]} { set zn_drv $zn_t }
    }
    set zn_w $zn_nx
  }
  if {$zn_drv eq ""} { incr zn_skip; continue }
  while {[$zn_blk findInst "u_fl_nl_$zn_k"] ne "NULL"} { incr zn_k }
  set zn_l [odb::dbInst_create $zn_blk $zn_m "u_fl_nl_$zn_k"]
  set zn_q [odb::dbNet_create $zn_blk "fl_nl_$zn_k"]
  incr zn_k
  $zn_d disconnect
  [$zn_l findITerm D] connect $zn_net
  [$zn_l findITerm CLK] connect [$zn_ck getNet]
  [$zn_l findITerm Q] connect $zn_q
  $zn_d connect $zn_q
  incr zn_n
}
puts "OT_ZL_NETLIST inserted $zn_n lockup latches ([llength $zn_res] patterns, [dict size $zn_exact] exact, [llength $zn_excl] excluded, $zn_skip matching registers not a direct register hop)"
