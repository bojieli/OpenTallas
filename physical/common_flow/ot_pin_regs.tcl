# OT_PIN_REGS (OWNER RULE 19:50 PT 2026-10-15, ROOT): every NEW tile registers every input and every output at its pin.
# Sourced first by ot_keep_regs.tcl (ORFS SYNTH_CANONICALIZE_TCL hook, right after `hierarchy -check -top`) when
# OT_PIN_REGS=1 (tools/ref_tile/ref_tile.py recipe 3 sets it).  The elaborated top module is renamed <top>__ot_pr_core and
# a generated wrapper module <top> with the SAME ports puts one flip-flop on every data input and every output (keep),
# clocked by OT_PIN_REGS_CLOCK. Excluded (wired straight through): literal clock/reset roles
# (OT_PIN_REGS_CLOCK / required OT_PIN_REGS_RESET_PORTS), OT_PIN_REGS_EXCLUDE (recorded regexp), and inouts.  Latency: +1 cycle per
# registered input, +1 per registered output; the table goes to $RESULTS_DIR/ot_pin_regs.tsv (port dir width cycles).
# io_flop_at_pins.tcl then anchors these flops at their pin faces (recipe 2/3 pin hook).
# RESET LANDING (ROOT-RST 2026-10-19, OT_RST_LAND=1, ref_tile "reset_landing"): every declared reset port lands in
# OT_RST_LAND_STAGES (default 2) plain registers <port>__ot_rl0 -> <port>__ot_rl1 (keep) clocked by the data clock before
# the core: the port net has one sink (io_flop_at_pins anchors rl0 at the pin) and the core's reset fan-out starts at a
# register (equal-depth tree by repair_design) instead of an unregistered buffer tree from the pin (qkd_kvs_attn rst_n
# capture 383.3, ot_s81_kp4_dec rst_n 648 ps / TT -70).  Assertion and release are delayed by STAGES cycles (a scheduled
# constant); the table row stays "reset" 0 cycles (data latency) and $RESULTS_DIR/ot_rst_land.tsv records the stages.
# With OT_RST_LAND=1 and OT_PIN_REGS!=1 (landing only) every data port passes straight through and the wrapper is written
# as ot_rst_land_wrapper.v (no pin-register table: the kit registers no data pin here).
set ot_pr_regs [expr {!([info exists ::env(OT_RST_LAND)] && $::env(OT_RST_LAND) eq "1") || ([info exists ::env(OT_PIN_REGS)] && $::env(OT_PIN_REGS) eq "1")}]
set ot_rl_on [expr {[info exists ::env(OT_RST_LAND)] && $::env(OT_RST_LAND) eq "1"}]
set ot_rl_n [expr {[info exists ::env(OT_RST_LAND_STAGES)] && [string is integer -strict $::env(OT_RST_LAND_STAGES)] ? $::env(OT_RST_LAND_STAGES) : 2}]
if {$ot_rl_on && ($ot_rl_n < 1 || $ot_rl_n > 4)} { error "OT_RST_LAND: OT_RST_LAND_STAGES must be 1..4, got $ot_rl_n" }
set ot_rl_distributed [expr {[info exists ::env(OT_RST_LAND_DISTRIBUTED)] && $::env(OT_RST_LAND_DISTRIBUTED) eq "1"}]
if {$ot_rl_distributed && $ot_rl_n < 3} { error "distributed reset chain needs >=3 stages" }
set ot_rl_fc [dict create]
if {[info exists ::env(OT_RST_LAND_FIRST_COPIES)] && [string trim $::env(OT_RST_LAND_FIRST_COPIES)] ne ""} {
  foreach it [split $::env(OT_RST_LAND_FIRST_COPIES) ","] {
    if {![regexp {^([A-Za-z_][A-Za-z0-9_]*)=([0-9]+)$} [string trim $it] -> cpn cpc] || $cpc < 1 || $cpc > 32} {
      error "OT_RST_LAND_FIRST_COPIES: expected port=N (1..32), got $it"
    }
    if {$ot_rl_n != 2 && !$ot_rl_distributed} { error "OT_RST_LAND_FIRST_COPIES requires exactly two stages" }
    dict set ot_rl_fc $cpn $cpc
  }
}
set ot_rl_cp [dict create]
if {[info exists ::env(OT_RST_LAND_COPIES)] && [string trim $::env(OT_RST_LAND_COPIES)] ne ""} {
  foreach it [split $::env(OT_RST_LAND_COPIES) ","] {
    if {![regexp {^([A-Za-z_][A-Za-z0-9_]*)=([0-9]+)$} [string trim $it] -> cpn cpc] || $cpc < 1 || $cpc > [expr {[dict exists $ot_rl_fc $cpn] ? 1024 : 64}]} {
      error "OT_RST_LAND_COPIES: expected port=N (1..64), got $it"
    }
    dict set ot_rl_cp $cpn $cpc
  }
}
dict for {p f} $ot_rl_fc {
  if {![dict exists $ot_rl_cp $p] || [dict get $ot_rl_cp $p] > 32*$f} {
    error "balanced reset requires final copies and <=32 final per first"
  }
  if {![info exists ::env(OT_RST_COPIES_MAX)] || $::env(OT_RST_COPIES_MAX) > 32} {
    error "balanced reset requires OT_RST_COPIES_MAX <=32"
  }
}
set ot_pr_top $::env(DESIGN_NAME)
set ot_pr_clk [split [expr {[info exists ::env(OT_PIN_REGS_CLOCK)] ? $::env(OT_PIN_REGS_CLOCK) : ""}] ","]
if {![llength $ot_pr_clk]} { error "OT_PIN_REGS: OT_PIN_REGS_CLOCK not set" }
if {![info exists ::env(OT_PIN_REGS_RESET_PORTS)]} {
  error "OT_PIN_REGS: missing literal reset roles (OT_PIN_REGS_RESET_PORTS); regenerate the kit, including an explicit empty list when no resets exist"
}
# Legacy regex/default was part of the accepted wrapper contract. Check its
# population before transformation so adding exact roles cannot silently turn
# a previously bypassed reset into data. Explicit declarations are required;
# the regex is a compatibility check, not a new semantic classification.
set ot_pr_legacy_reset [expr {[info exists ::env(OT_PIN_REGS_RESET)] && $::env(OT_PIN_REGS_RESET) ne "" ? $::env(OT_PIN_REGS_RESET) :
                            {(?i)(^|_)(a?s?rst|reset|rstn|resetn|rst_n|rst_ni|reset_n|reset_ni|por|por_n)(_|$)}}]
set ot_pr_exc [expr {[info exists ::env(OT_PIN_REGS_EXCLUDE)] ? $::env(OT_PIN_REGS_EXCLUDE) : ""}]
set ot_pr_dir [expr {[info exists ::env(RESULTS_DIR)] ? $::env(RESULTS_DIR) : "."}]
yosys tee -q -o $ot_pr_dir/ot_pin_regs.ports portlist $ot_pr_top
set f [open $ot_pr_dir/ot_pin_regs.ports r]; set ot_pr_lines [split [read $f] "\n"]; close $f
set ports {}
foreach ln $ot_pr_lines {
  if {[regexp {^(input|output|inout)\s+\[(\d+):(\d+)\]\s+(\S+)$} [string trim $ln] -> d a b n]} { lappend ports [list $d $a $b $n] }
}
if {![llength $ports]} { error "OT_PIN_REGS: no ports read for $ot_pr_top" }
set ck [lindex $ot_pr_clk 0]
# Resolve literal declarations against the elaborated bit ranges. Do not turn
# a declared clock/reset into data because of a spelling/range mismatch.
proc ot_pr_resolve_roles {ports names role} {
  set selected {}
  foreach name $names {
    if {$name eq ""} continue
    if {![regexp {^([A-Za-z_][A-Za-z0-9_$]*)(?:\[([0-9]+)\])?$} $name -> base bit]} {
      error "OT_PIN_REGS: $role must be a literal port or bit: $name"
    }
    set index [lsearch -index 3 -exact $ports $base]
    if {$index < 0} {error "OT_PIN_REGS: declared $role $name is not an elaborated port"}
    lassign [lindex $ports $index] dir a b n
    if {$bit ne "" && ($bit < min($a,$b) || $bit > max($a,$b))} {
      error "OT_PIN_REGS: declared $role bit out of range: $name"
    }
    for {set i [expr {min($a,$b)}]} {$i <= max($a,$b)} {incr i} {
      if {$bit eq "" || $bit == $i} {dict set selected $base $i 1}
    }
  }
  set whole {}
  dict for {base bits} $selected {
    lassign [lindex $ports [lsearch -index 3 -exact $ports $base]] dir a b n
    if {[dict size $bits] != abs($a-$b)+1} {
      error "OT_PIN_REGS: mixed-role bus $base needs an explicit boundary wrapper; refusing partial $role classification"
    }
    lappend whole $base
  }
  return $whole
}
set ot_pr_clock_ports [ot_pr_resolve_roles $ports $ot_pr_clk clock]
set ot_pr_reset_ports {}
set ot_pr_reset_ports [ot_pr_resolve_roles $ports [split $::env(OT_PIN_REGS_RESET_PORTS) ","] reset]
foreach p $ports {
  set name [lindex $p 3]
  if {[regexp -- $ot_pr_legacy_reset $name] && $name ni $ot_pr_reset_ports && $name ni $ot_pr_clock_ports} {
    error "OT_PIN_REGS: legacy reset regexp/default matches undeclared reset $name; add its literal reset_ports declaration and regenerate before transformation"
  }
}
foreach name $ot_pr_clock_ports {
  if {$name in $ot_pr_reset_ports} {error "OT_PIN_REGS: conflicting clock/reset role: $name"}
}
# The chosen data clock is one literal bit; a multi-bit bus is ambiguous.
regexp {^([^\[]+)(?:\[([0-9]+)\])?$} $ck -> ckbase ckbit
lassign [lindex $ports [lsearch -index 3 -exact $ports $ckbase]] ckdir cka ckb ckn
if {$ckdir ne "input" || ($ckbit eq "" && $cka != $ckb)} {
  error "OT_PIN_REGS: data clock must be one literal input bit: $ck"
}
set core "${ot_pr_top}__ot_pr_core"
set v "// generated by physical/common_flow/ot_pin_regs.tcl ([expr {$ot_pr_regs ? {OT_PIN_REGS=1} : {OT_RST_LAND=1}}])\nmodule $ot_pr_top ([join [lmap p $ports {lindex $p 3}] {, }]);\n"
set conn {}; set tsv "port\tdir\twidth\tcycles\twhy\n"; set nreg 0
set rl_tsv "port\twidth\tstages\tclock\n"; set nland 0
foreach p $ports {
  lassign $p d a b n
  set w [expr {abs($a - $b) + 1}]
  # A width-1 port at bit 0 is declared scalar: yosys portlist prints scalars as [0:0], and a [0:0] wrapper port
  # renames the BTerm to n[0] (vm_native_q* nat2 gate: "ASSIGNED_PIN_EXACT missing BTerm clk").
  if {$a == 0 && $b == 0} { append v "  $d $n;\n" } else { append v "  $d \[$a:$b\] $n;\n" }
  set why ""
  if {[lsearch -exact $ot_pr_clock_ports $n] >= 0} { set why clock
  } elseif {$d eq "inout"} { set why inout
  } elseif {$n in $ot_pr_reset_ports} { set why reset
  } elseif {$ot_pr_exc ne "" && [regexp -- $ot_pr_exc $n]} { set why excluded
  } elseif {!$ot_pr_regs} { set why excluded }
  if {$why eq "reset" && $ot_rl_on && $d eq "input"} {
    # RESET LANDING: port -> rl0 -> ... -> rl<N-1> -> core
    set prev $n
    for {set k 0} {$k < $ot_rl_n} {incr k} {
      append v "  (* keep *) reg \[$a:$b\] ${n}__ot_rl$k;\n  always @(posedge $ck) ${n}__ot_rl$k <= $prev;\n"
      set prev "${n}__ot_rl$k"
    }
    if {[dict exists $ot_rl_fc $n] && [dict get $ot_rl_fc $n] > 1} {
      set f [dict get $ot_rl_fc $n]
      if {$w != 1} { error "balanced reset needs scalar reset" }
      # Both families are identical in the immutable pre-rewire snapshot.
      # Split first-stage D loads over these equal copies, then core reset loads
      # over the final family. No edge is added and signatures stay strict.
      append v "  (* keep *) reg \[[expr {$f - 2}]:0\] ${n}__ot_rl0c;\n  always @(posedge $ck) ${n}__ot_rl0c <= {[expr {$f - 1}]{$n}};\n"
      append v "  wire \[[expr {$f - 1}]:0\] ${n}__ot_rl0v = {${n}__ot_rl0c, ${n}__ot_rl0};\n"
    }
    # Opt-in equal-depth distributed reset. Every intermediate level has its own identical copy family, proved
    # together on the immutable pre-rewire snapshot by ot_rst_copies.py. The physical hook may put each chain along
    # a <=405-um path; all paths still take exactly OT_RST_LAND_STAGES clocks, including assertion.
    if {$ot_rl_distributed} {
      if {![dict exists $ot_rl_fc $n] || ![dict exists $ot_rl_cp $n]} { error "distributed reset needs first/final copies" }
      set c [dict get $ot_rl_cp $n]
      for {set k 1} {$k < $ot_rl_n - 1} {incr k} {
        append v "  (* keep *) reg \[[expr {$c - 2}]:0\] ${n}__ot_rl${k}c;\n  always @(posedge $ck) ${n}__ot_rl${k}c <= {[expr {$c - 1}]{${n}__ot_rl[expr {$k - 1}]}};\n"
        append v "  wire \[[expr {$c - 1}]:0\] ${n}__ot_rl${k}v = {${n}__ot_rl${k}c, ${n}__ot_rl${k}};\n"
      }
    }
    # KV-RELAYGEN 2026-10-19 (OT_RST_LAND_COPIES "port=N,..."): the last landing stage gets N-1 KEPT identical copies
    # <port>__ot_rlc beside it; <port>__ot_rlv = {copies, last stage} is the copy family that ot_rst_copies.tcl spreads
    # the core's reset loads over (<= OT_RST_COPIES_MAX each).  The chain text and the core connection are unchanged.
    if {[dict exists $ot_rl_cp $n] && [dict get $ot_rl_cp $n] > 1} {
      set c [dict get $ot_rl_cp $n]
      if {$w != 1} { error "OT_RST_LAND_COPIES: $n is $w bits wide (copies need a 1-bit reset)" }
      append v "  (* keep *) reg \[[expr {$c - 2}]:0\] ${n}__ot_rlc;\n  always @(posedge $ck) ${n}__ot_rlc <= {[expr {$c - 1}]{${n}__ot_rl[expr {$ot_rl_n - 2}]}};\n"
      append v "  wire \[[expr {$c - 1}]:0\] ${n}__ot_rlv = {${n}__ot_rlc, $prev};\n"
      if {$ot_rl_n < 2} { error "OT_RST_LAND_COPIES: needs OT_RST_LAND_STAGES >= 2" }
    }
    lappend conn ".$n\($prev\)"; append tsv "$n\t$d\t$w\t0\treset\n"
    append rl_tsv "$n\t$w\t$ot_rl_n\t$ck\n"; incr nland
    continue
  }
  if {$why ne ""} {
    lappend conn ".$n\($n\)"; append tsv "$n\t$d\t$w\t0\t$why\n"; continue
  }
  append v "  wire \[$a:$b\] ${n}__ot_pr;\n  (* keep *) reg \[$a:$b\] ${n}__ot_q;\n"
  if {$d eq "input"} {
    append v "  always @(posedge $ck) ${n}__ot_q <= $n;\n  assign ${n}__ot_pr = ${n}__ot_q;\n"
  } else {
    append v "  always @(posedge $ck) ${n}__ot_q <= ${n}__ot_pr;\n  assign $n = ${n}__ot_q;\n"
  }
  lappend conn ".$n\(${n}__ot_pr\)"; append tsv "$n\t$d\t$w\t1\tpin register\n"; incr nreg
}
append v "  $core u_ot_pr_core ([join $conn {, }]);\nendmodule\n"
if {$ot_rl_on && !$nland} { error "OT_RST_LAND: no declared input reset port to land (OT_PIN_REGS_RESET_PORTS)" }
set ot_pr_wrapper [expr {$ot_pr_regs ? "$ot_pr_dir/ot_pin_regs_wrapper.v" : "$ot_pr_dir/ot_rst_land_wrapper.v"}]
set f [open $ot_pr_wrapper w]; puts -nonewline $f $v; close $f
if {$ot_pr_regs} { set f [open $ot_pr_dir/ot_pin_regs.tsv w]; puts -nonewline $f $tsv; close $f }
if {$ot_rl_on} { set f [open $ot_pr_dir/ot_rst_land.tsv w]; puts -nonewline $f $rl_tsv; close $f }
yosys rename $ot_pr_top $core
yosys read_verilog -sv $ot_pr_wrapper
yosys hierarchy -check -top $ot_pr_top
if {$ot_pr_regs} { puts "OT_PIN_REGS $ot_pr_top: $nreg of [llength $ports] ports registered at the pin (clock $ck); table $ot_pr_dir/ot_pin_regs.tsv" }
if {$ot_rl_on} { puts "OT_RST_LAND $ot_pr_top: $nland reset port(s) landed in $ot_rl_n registered stage(s) (clock $ck); table $ot_pr_dir/ot_rst_land.tsv" }
