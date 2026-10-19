# KV-PEER5 (REFILL-1330, 2026-10-19): RESET RELAY COPIES.  Sourced by physical/common_flow/ot_keep_regs.tcl (ORFS
# SYNTH_CANONICALIZE_TCL) at its end when OT_RST_SPLIT=1, i.e. after `proc` and after the keep marking.
#
# Why: a member wrapper's ot_rst_relay output drove the member's whole async-reset tree from ONE kept flop (qkd_hr_core_peer
# r4: 5,165 / 2,165 / 1,260 / 893 loads; SAFE-DESIGN checklist item 3 wants <= ~256 per copy, kept, regionally placed).
# The member's reset is one input port, so the RTL cannot hand different copies to different flops without forking every
# member.  The wrapper instead instantiates ot_rst_relay #(REGIONS K) and declares its K identical kept outputs as
#     (* keep, ot_rst_split *) wire [K-1:0] <r>_qv;   wire <r>_q = <r>_qv[0];   member .<r>(<r>_q)
# and this hook, for every module holding such a wire: flattens that module (the member and the relay are inlined), maps
# its async-reset flip-flops to single-bit cells, finds every flop whose async reset (R / S / L) is <r>_qv[0] (through the
# module's alias connections), sorts them by name (the RTL register order: bits of one register and registers of one
# sub-unit stay together, which placement keeps together) and moves group k of K equal groups onto <r>_qv[k].
# Function is unchanged: the copies are the same register (same D, clock and async clear), each stays a kept flop
# (ot_keep_regs.tcl), so opt_merge cannot fold them back, and placement puts each copy with its group.  Data uses of the
# reset (rst_n read as a level) stay on copy 0.
#   OT_RST_SPLIT=1        enable (ref_tile spec "rst_split": true writes it into the kit)
#   OT_RST_SPLIT_MAX=256  error out when a copy would drive more loads than this (the RTL K is too small)
# Report: one line per split wire, and $RESULTS_DIR/ot_rst_split.tsv (module wire copies loads max_per_copy).
set ot_rs_max [expr {[info exists ::env(OT_RST_SPLIT_MAX)] && [string is integer -strict $::env(OT_RST_SPLIT_MAX)] ? $::env(OT_RST_SPLIT_MAX) : 256}]
set ot_rs_dir [expr {[info exists ::env(RESULTS_DIR)] ? $::env(RESULTS_DIR) : "."}]
set ot_rs_objs {}
foreach ln [split [string trim [yosys tee -q -s result.string select -list w:* a:ot_rst_split %i]] "\n"] {
  set ln [string trim $ln]
  if {$ln eq ""} continue
  set i [string last "/" $ln]
  lappend ot_rs_objs [list [string range $ln 0 [expr {$i - 1}]] [string range $ln [expr {$i + 1}] end]]
}
if {![llength $ot_rs_objs]} { error "OT_RST_SPLIT: no wire with attribute ot_rst_split in the design (regenerate the wrappers)" }
set ot_rs_tsv "module\twire\tcopies\tloads\tmax_per_copy\n"
set ot_rs_mods [lsort -unique [lmap o $ot_rs_objs {lindex $o 0}]]
foreach ot_rs_m $ot_rs_mods {
  # inline the member (and the relay) into the wrapper; async flops -> single-bit cells
  yosys flatten $ot_rs_m
  yosys techmap {*}[list $ot_rs_m/t:\$adff $ot_rs_m/t:\$adffe $ot_rs_m/t:\$dffsr $ot_rs_m/t:\$dffsre $ot_rs_m/t:\$aldff $ot_rs_m/t:\$aldffe]
  yosys opt_clean $ot_rs_m
  set f [file join $ot_rs_dir ot_rst_split_dump.il]
  yosys tee -q -o $f dump $ot_rs_m
  set fh [open $f r]; set il [read $fh]; close $fh; if {![info exists ::env(OT_RST_SPLIT_KEEP_DUMP)]} { file delete $f }
  # bit-level alias closure over the module's connections (connect <lhs> <rhs>; names, [i], [i:j], { concatenations })
  array unset ot_rs_par; array unset ot_rs_w
  set ot_rs_cells {}; set cur ""; set ctype ""; set conns {}
  foreach l [split $il "\n"] {
    set l [string trim $l]
    if {[string match "wire *" $l]} {
      set ws [split $l " "]
      set ot_rs_w([lindex $ws end]) [expr {[regexp {^wire width (\d+) } $l -> kw] ? $kw : 1}]
      continue
    }
    if {[regexp {^cell (\S+) (\S+)$} $l -> ctype cur]} { continue }
    if {$l eq "end"} { set cur ""; continue }
    if {![string match "connect *" $l]} continue
    if {$cur eq ""} { lappend conns [string range $l 8 end]; continue }
    if {[regexp {^\$_(DFF|DFFE|DFFSR|DFFSRE|ALDFF|ALDFFE)_} $ctype] && [regexp {^connect \\(R|S|L) (.+)$} $l -> port sig]} {
      lappend ot_rs_cells [list $cur $port $sig]
    }
  }
  # one side of a connect -> list of bit ids "name#i" (LSB first); constants -> unique dummies
  proc ot_rs_bits {side} {
    upvar #0 ot_rs_w W
    set side [string trim $side]
    if {[string index $side 0] eq "\{"} {
      set inner [string trim [string range $side 1 end-1]]
      set toks [regexp -all -inline {\S+(?: \[\d+(?::\d+)?\])?} $inner]
      set out {}
      foreach tk [lreverse $toks] { lappend out {*}[ot_rs_bits $tk] }
      return $out
    }
    if {[regexp {^(\S+) \[(\d+)\]$} $side -> n i]} { return [list "$n#$i"] }
    if {[regexp {^(\S+) \[(\d+):(\d+)\]$} $side -> n hi lo]} {
      set out {}; for {set i $lo} {$i <= $hi} {incr i} { lappend out "$n#$i" }; return $out
    }
    if {[info exists W($side)]} {
      set out {}; for {set i 0} {$i < $W($side)} {incr i} { lappend out "$side#$i" }; return $out
    }
    return [list "const:[incr ::ot_rs_cn]"]
  }
  proc ot_rs_find {x} { upvar #0 ot_rs_par P; while {[info exists P($x)] && $P($x) ne $x} { set x $P($x) }; return $x }
  foreach c $conns {
    # split "<lhs> <rhs>": the lhs is a { } group or a name with an optional [..] index
    if {[string index $c 0] eq "\{"} { set j [string first "\}" $c]; set lhs [string range $c 0 $j]; set rhs [string range $c [expr {$j + 1}] end]
    } elseif {[regexp {^(\S+(?: \[\d+(?::\d+)?\])?) (.+)$} $c -> lhs rhs]} {
    } else continue
    set lb [ot_rs_bits $lhs]; set rb [ot_rs_bits $rhs]
    if {[llength $lb] != [llength $rb]} continue
    foreach a $lb b $rb {
      set ra [ot_rs_find $a]; set rb2 [ot_rs_find $b]
      if {$ra ne $rb2} { set ot_rs_par($ra) $rb2 }
    }
  }
  foreach o $ot_rs_objs {
    if {[lindex $o 0] ne $ot_rs_m} continue
    set w [lindex $o 1]
    # copies = the wire's width (select -list prints the wire name without its leading backslash)
    set k 0
    foreach l [split $il "\n"] {
      set l [string trim $l]
      if {[string match "wire *" $l] && [lindex [split $l " "] end] eq "\\$w"} {
        set k [expr {[regexp {^wire width (\d+) } $l -> kw] ? $kw : 1}]
      }
    }
    if {!$k} { error "OT_RST_SPLIT: wire $w not found in $ot_rs_m after flatten" }
    set root [ot_rs_find "\\$w#0"]
    set loads {}
    foreach c $ot_rs_cells {
      lassign $c cn port sig
      set sb [ot_rs_bits $sig]
      if {[llength $sb] == 1 && [ot_rs_find [lindex $sb 0]] eq $root} { lappend loads [list $cn $port] }
    }
    set n [llength $loads]
    if {$k < 2 || $n == 0} {
      puts "OT_RST_SPLIT $ot_rs_m $w: $n async loads, $k copy(ies): nothing to split"
      append ot_rs_tsv "$ot_rs_m\t$w\t$k\t$n\t$n\n"; continue
    }
    set loads [lsort -dictionary -index 0 $loads]
    set per [expr {($n + $k - 1) / $k}]
    if {$per > $ot_rs_max} { error "OT_RST_SPLIT: $ot_rs_m $w: $n loads over $k copies = $per a copy > OT_RST_SPLIT_MAX $ot_rs_max (raise K in the wrapper generator)" }
    yosys cd $ot_rs_m
    set i 0
    foreach ld $loads {
      set g [expr {$i / $per}]
      if {$g > 0} { yosys connect -port [lindex $ld 0] [lindex $ld 1] "$w\[$g\]" }
      incr i
    }
    yosys cd ..
    puts "OT_RST_SPLIT $ot_rs_m $w: $n async-reset loads over $k kept copies (<= $per a copy)"
    append ot_rs_tsv "$ot_rs_m\t$w\t$k\t$n\t$per\n"
  }
}
set fh [open [file join $ot_rs_dir ot_rst_split.tsv] w]; puts -nonewline $fh $ot_rs_tsv; close $fh
