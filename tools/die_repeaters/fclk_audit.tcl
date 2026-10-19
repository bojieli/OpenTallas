# Forwarded-clock vs data repeater audit for the shared die repeater step (H-REACH 2026-10-17; DIE-CLOCK conditions
# 1 and 4 for repeaters on forwarded-clock nets: a hop's fclk and its data bits are repaired in one pass with the same
# max wire and buffer list, and their repeater stage counts must match within +-1).
#
#   ot_die_rep_fclk_snapshot              before ot_die_repeaters: remembers the pre-existing instance names
#   ot_die_rep_fclk_audit PREFIX GLOBS ?BUFFERS?
#                                          after it: for every net matching GLOBS (the forwarded clocks, e.g. n_*_fck*
#                                          or the S81 fo0 -> fi0 nets) that has a driver:
#     * src   = the driving instance of the fclk net (not a new repeater);
#     * walk forward from the driver through NEW repeaters (instances created after the snapshot whose master is in
#       BUFFERS) to every first non-repeater load t; fclk depth(t) = repeaters on that path;
#     * at each such t, walk BACK from every other input pin through new repeaters to its source; the bits whose source
#       is src are that hop's data bits; data depth = repeaters on their path;
#     * a hop (src, t) is a mismatch when |fclk depth - data depth| > 1 for any of its data bits.
#   (v2: structural pairing + broadcast flag + vacuous = FAIL; see the proc.)  Writes PREFIX.tsv / PREFIX.json; returns mismatching
#   hops (0 = within budget).  Hops with no data bit from the same source are listed (data_bits 0) but not judged.

proc ot_die_rep_fclk_snapshot {} {
  global ot_die_rep_fclk_old
  array unset ot_die_rep_fclk_old
  foreach inst [[ord::get_db_block] getInsts] { set ot_die_rep_fclk_old([$inst getName]) 1 }
  return [array size ot_die_rep_fclk_old]
}

proc ot_die_rep_fclk_is_rep {inst bufs} {
  global ot_die_rep_fclk_old
  if {[info exists ot_die_rep_fclk_old([$inst getName])]} { return 0 }
  return [expr {[lsearch -exact $bufs [[$inst getMaster] getName]] >= 0}]
}

# forward: {load_inst_name depth ...} over every first non-repeater load reachable through new repeaters
proc ot_die_rep_fclk_fwd {net bufs depth acc_name} {
  upvar 1 $acc_name acc
  foreach it [$net getITerms] {
    if {[$it getIoType] ne "INPUT"} continue
    set li [$it getInst]
    if {[ot_die_rep_fclk_is_rep $li $bufs]} {
      foreach o [$li getITerms] {
        if {[$o getIoType] eq "OUTPUT" && [$o getNet] ne "NULL"} { ot_die_rep_fclk_fwd [$o getNet] $bufs [expr {$depth + 1}] acc }
      }
    } else {
      dict set acc [$li getName] [list $depth [$it getMTerm]]
    }
  }
}

# backward from an input iterm: {source_inst_name depth source_output_mterm_name}
proc ot_die_rep_fclk_back {iterm bufs} {
  set d 0; set it $iterm
  for {set guard 0} {$guard < 10000} {incr guard} {
    set net [$it getNet]
    if {$net eq "NULL"} { return [list {} $d] }
    set drv {}
    foreach x [$net getITerms] { if {[$x getIoType] eq "OUTPUT"} { set drv $x; break } }
    if {$drv eq ""} { return [list {} $d] }
    set di [$drv getInst]
    if {![ot_die_rep_fclk_is_rep $di $bufs]} { return [list [$di getName] $d [[$drv getMTerm] getName]] }
    incr d
    set it {}
    foreach x [$di getITerms] { if {[$x getIoType] eq "INPUT" && [$x getNet] ne "NULL" && ![[$x getNet] isSpecial]} { set it $x; break } }
    if {$it eq ""} { return [list {} $d] }
  }
  return [list {} $d]
}

# Optional producer contract: ::ot_die_rep_fclk_data_ports maps exact capture
# master names to {data-pin-glob expected-bit-count}. Auxiliary reset/control
# inputs are outside the forwarded data hop. Missing/untraceable declared bits
# fail closed; depth and broadcast rules remain unchanged.
proc ot_die_rep_fclk_audit {prefix globs {bufs {BUFx4_ASAP7_75t_R BUFx4f_ASAP7_75t_R BUFx5_ASAP7_75t_R BUFx6f_ASAP7_75t_R BUFx8_ASAP7_75t_R}}} {
  # Structural pairing (2026-10-17, DIE-CLOCK on S81-DV p4c: names never matter):
  #   for every fclk net F and every capture instance t reached by F (forward through new repeaters, fclk depth f):
  #     the data bits of the hop into t are t's other input pins; each is walked back through new repeaters to its
  #     source instance s (data depth d).  Bits whose source is F's own driver are preferred (macro stations: fo0 and
  #     do0 leave the same instance); otherwise every traced data input of t is taken (std-cell DFF relays: the clock
  #     arrives from a forwarding cell, the data from the previous stage's flops).  Inputs on special nets or with no
  #     driver are ignored.
  #   BROADCAST: F is a broadcast (one fclk net per chain, not per hop) when a data source of one of its capture
  #     instances is itself a capture instance of F; its hops are flagged and NOT judged (fclk depth vs data depth has
  #     no per-hop meaning there).
  #   FAIL CLOSED: fclk nets present but zero judged hops (all broadcast or no data pairs) -> the return value counts
  #     it as a violation (vacuous = fail), as do mismatches (|f - d| > 1) and broadcasts.
  global ot_die_rep_fclk_old ot_die_rep_fclk_data_ports
  if {![array exists ot_die_rep_fclk_old]} { error "ot_die_rep_fclk_audit: call ot_die_rep_fclk_snapshot before the repair" }
  set blk [ord::get_db_block]
  set nets {}
  foreach n [$blk getNets] {
    set nm [$n getName]
    foreach g $globs { if {[string match $g $nm]} { lappend nets $n; break } }
  }
  set f [open $prefix.tsv w]
  puts $f "fclk_net\tfclk_src\tcapture\tfclk_repeaters\tdata_min\tdata_max\tdata_bits\tpairing\tbroadcast\tmismatch\tauxiliary_inputs\tconstant_bits"
  set hops 0; set judged 0; set bad 0; set bcast_nets 0; set bcast_hops 0; set fnets 0; set pairing_errors 0; set constant_bits 0; set examples {}
  foreach n $nets {
    set drv {}
    foreach x [$n getITerms] { if {[$x getIoType] eq "OUTPUT"} { set drv $x; break } }
    if {$drv eq ""} continue
    if {[ot_die_rep_fclk_is_rep [$drv getInst] $bufs]} continue       ;# a repeater-side segment of an fclk net
    incr fnets
    set src [[$drv getInst] getName]
    set acc [dict create]
    ot_die_rep_fclk_fwd $n $bufs 0 acc
    # per capture: traced data inputs {source depth}
    set rows {}
    set is_bcast 0
    dict for {load v} $acc {
      lassign $v fdepth fmterm
      set li [$blk findInst $load]
      set same {}; set any {}; set declared {}; set selected 0; set aux 0; set const 0
      set contract {}
      set master [[$li getMaster] getName]
      if {[info exists ot_die_rep_fclk_data_ports] && [dict exists $ot_die_rep_fclk_data_ports $master]} {
        set contract [dict get $ot_die_rep_fclk_data_ports $master]
        lassign $contract pattern expected
        if {![string is integer -strict $expected] || $expected <= 0} { error "invalid fclk data-port contract for $master" }
      }
      foreach it [$li getITerms] {
        if {[$it getIoType] ne "INPUT"} continue
        if {[$it getMTerm] eq $fmterm} continue
        if {[llength $contract]} {
          if {![string match $pattern [[$it getMTerm] getName]]} { incr aux; continue }
          incr selected
        }
        if {[$it getNet] eq "NULL" || [[$it getNet] isSpecial]} continue
        lassign [ot_die_rep_fclk_back $it $bufs] s d source_pin
        if {$s eq ""} continue
        # Physical constant drivers are accounted payload pins, but have no
        # switching data launch to match to the forwarded clock. Recognize the
        # exact native tie cell AND its actual constant output, never a net name
        # or an undriven "constant" wire. A buffer chain may end at this tie.
        if {$source_pin ne ""} {
          set source_inst [$blk findInst $s]
          set source_master [[$source_inst getMaster] getName]
          if {($source_master eq "TIEHIx1_ASAP7_75t_R" && $source_pin eq "H") ||
              ($source_master eq "TIELOx1_ASAP7_75t_R" && $source_pin eq "L")} {
            incr const; incr constant_bits; continue
          }
        }
        lappend declared $d
        if {[dict exists $acc $s]} { set is_bcast 1 }
        if {$s eq $src} { lappend same $d } else { lappend any $d }
      }
      if {[llength $contract]} {
        # The producer declares the complete functional data bus. Never prefer a
        # same-source subset here: every data bit must be traced and judged.
        set ds $declared; set how data_port_contract
        if {$selected != $expected || [llength $ds] + $const != $expected} { incr pairing_errors; set how data_port_contract_ERROR }
      } elseif {[llength $same]} { set ds $same; set how same_source } elseif {[llength $any]} { set ds $any; set how capture_inputs } else { set ds {}; set how none }
      lappend rows [list $load $fdepth $ds $how $aux $const]
    }
    if {$is_bcast} { incr bcast_nets }
    foreach r $rows {
      lassign $r load fdepth ds how aux const
      incr hops
      set dmin -1; set dmax -1; set mm 0
      if {[llength $ds]} { set dmin [tcl::mathfunc::min {*}$ds]; set dmax [tcl::mathfunc::max {*}$ds] }
      if {$is_bcast} {
        incr bcast_hops
      } elseif {[llength $ds]} {
        incr judged
        set mm [expr {abs($fdepth - $dmin) > 1 || abs($fdepth - $dmax) > 1}]
        if {$mm} { incr bad; if {[llength $examples] < 20} { lappend examples "[$n getName] $src->$load fclk=$fdepth data=$dmin..$dmax" } }
      }
      puts $f "[$n getName]\t$src\t$load\t$fdepth\t$dmin\t$dmax\t[llength $ds]\t$how\t$is_bcast\t$mm\t$aux\t$const"
    }
  }
  close $f
  set vacuous [expr {$fnets > 0 && $judged == 0}]
  set ex {}; foreach e $examples { lappend ex "\"[string map {\\ \\\\ \" \\\"} $e]\"" }
  set j [open $prefix.json w]
  puts $j "{\"schema\": \"opentallas.die_repeaters.fclk_audit.v3\", \"rule\": \"DIE-CLOCK: per hop |fclk repeaters - data repeaters| <= 1; pairing complete declared payload when provided (width and trace checked), otherwise capture inputs with same-source preferred; broadcast fclk nets flagged, not judged; fclk present with zero judged hops = vacuous = FAIL\", \"fclk_nets\": $fnets, \"broadcast_fclk_nets\": $bcast_nets, \"hops\": $hops, \"broadcast_hops\": $bcast_hops, \"hops_judged\": $judged, \"mismatch_over_1\": $bad, \"vacuous\": $vacuous, \"pairing_errors\": $pairing_errors, \"constant_bits\": $constant_bits, \"verdict\": \"[expr {($bad || $vacuous || $bcast_nets || $pairing_errors) ? {FAIL} : {PASS}}]\", \"examples\": \[[join $ex {, }]\], \"tsv\": \"[file tail $prefix].tsv\"}"
  close $j
  puts "OT_DIE_REP_FCLK fclk_nets=$fnets broadcast_nets=$bcast_nets hops=$hops judged=$judged mismatch_over_1=$bad pairing_errors=$pairing_errors vacuous=$vacuous"; flush stdout
  return [expr {$bad + $vacuous + $bcast_nets + $pairing_errors}]
}
