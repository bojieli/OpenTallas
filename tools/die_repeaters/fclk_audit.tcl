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
#   Writes PREFIX.tsv (one line per hop) and PREFIX.json (counts, worst examples); returns the number of mismatching
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

# backward from an input iterm: {source_inst_name depth}
proc ot_die_rep_fclk_back {iterm bufs} {
  set d 0; set it $iterm
  for {set guard 0} {$guard < 10000} {incr guard} {
    set net [$it getNet]
    if {$net eq "NULL"} { return [list {} $d] }
    set drv {}
    foreach x [$net getITerms] { if {[$x getIoType] eq "OUTPUT"} { set drv $x; break } }
    if {$drv eq ""} { return [list {} $d] }
    set di [$drv getInst]
    if {![ot_die_rep_fclk_is_rep $di $bufs]} { return [list [$di getName] $d] }
    incr d
    set it {}
    foreach x [$di getITerms] { if {[$x getIoType] eq "INPUT" && [$x getNet] ne "NULL" && ![[$x getNet] isSpecial]} { set it $x; break } }
    if {$it eq ""} { return [list {} $d] }
  }
  return [list {} $d]
}

proc ot_die_rep_fclk_audit {prefix globs {bufs {BUFx4_ASAP7_75t_R BUFx4f_ASAP7_75t_R BUFx5_ASAP7_75t_R BUFx6f_ASAP7_75t_R BUFx8_ASAP7_75t_R}}} {
  global ot_die_rep_fclk_old
  if {![array exists ot_die_rep_fclk_old]} { error "ot_die_rep_fclk_audit: call ot_die_rep_fclk_snapshot before the repair" }
  set blk [ord::get_db_block]
  set nets {}
  foreach n [$blk getNets] {
    set nm [$n getName]
    foreach g $globs { if {[string match $g $nm]} { lappend nets $n; break } }
  }
  set f [open $prefix.tsv w]
  puts $f "fclk_net\tsrc\tload\tfclk_repeaters\tdata_min\tdata_max\tdata_bits\tmismatch"
  set hops 0; set judged 0; set bad 0; set examples {}
  set seen_src {}
  foreach n $nets {
    set drv {}
    foreach x [$n getITerms] { if {[$x getIoType] eq "OUTPUT"} { set drv $x; break } }
    if {$drv eq ""} continue
    set src [[$drv getInst] getName]
    if {[ot_die_rep_fclk_is_rep [$drv getInst] $bufs]} continue       ;# a repeater-side segment of an fclk net
    set acc [dict create]
    ot_die_rep_fclk_fwd $n $bufs 0 acc
    dict for {load v} $acc {
      lassign $v fdepth fmterm
      set li [$blk findInst $load]
      set dmin 1000000; set dmax -1; set nb 0
      foreach it [$li getITerms] {
        if {[$it getIoType] ne "INPUT" || [$it getNet] eq "NULL" || [[$it getNet] isSpecial]} continue
        if {[$it getMTerm] eq $fmterm} continue
        lassign [ot_die_rep_fclk_back $it $bufs] s d
        if {$s ne $src} continue
        incr nb
        if {$d < $dmin} { set dmin $d }
        if {$d > $dmax} { set dmax $d }
      }
      incr hops
      set mm 0
      if {$nb} {
        incr judged
        set mm [expr {abs($fdepth - $dmin) > 1 || abs($fdepth - $dmax) > 1}]
        if {$mm} { incr bad; if {[llength $examples] < 20} { lappend examples "[$n getName] $src->$load fclk=$fdepth data=$dmin..$dmax" } }
      } else { set dmin -1 }
      puts $f "[$n getName]\t$src\t$load\t$fdepth\t$dmin\t$dmax\t$nb\t$mm"
    }
  }
  close $f
  set ex {}; foreach e $examples { lappend ex "\"[string map {\\ \\\\ \" \\\"} $e]\"" }
  set j [open $prefix.json w]
  puts $j "{\"schema\": \"opentallas.die_repeaters.fclk_audit.v1\", \"rule\": \"DIE-CLOCK: |fclk repeaters - data repeaters| <= 1 per hop\", \"fclk_nets\": [llength $nets], \"hops\": $hops, \"hops_with_data\": $judged, \"mismatch_over_1\": $bad, \"examples\": \[[join $ex {, }]\], \"tsv\": \"[file tail $prefix].tsv\"}"
  close $j
  puts "OT_DIE_REP_FCLK fclk_nets=[llength $nets] hops=$hops judged=$judged mismatch_over_1=$bad"; flush stdout
  return $bad
}
