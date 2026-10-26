# die_clock_check.tcl -- dump the die clock network for tools/die_clock_check.py (ROOT 2026-10-16, coordinator direction).
#
# Source this INSIDE a die trial's OpenROAD session, after the die clock tree is in the db (placed) and, for the measured
# part, after the die STA is set up (read_sdc + set_propagated_clock + estimate_parasitics).  Shared by the S81, Qwen
# compute, Qwen KV/system and HBM die flows: it reads only the db (topology, cell masters, pin locations) and OpenSTA pin
# arrivals, nothing flow-specific.
#
#   set ::env(OT_DCC_OUT) /work/out/die_clock_dump.tsv   ;# required: where to write the dump
#   set ::env(OT_DCC_STA) 1                              ;# 1 (default): also read OpenSTA arrivals; 0: topology only
#   set ::env(OT_DCC_ROOTS) "clk ckgen/pll_clk"          ;# optional: root ports / inst/pin; default = SDC clock sources
#   set ::env(OT_DCC_MAX_FANOUT) 8                       ;# a data net joining 2..N tiles makes tile pairs (default 8)
#   source /work/die_clock_check.tcl
#   then: python3 tools/die_clock_check.py report /work/out/die_clock_dump.tsv --out die_clock_check.json
#
# Dump lines (tab separated):
#   R <node> <x_um> <y_um> <arr_max> <arr_min>                       clock root (port:NAME or inst/pin)
#   B <node> <cell> <x_um> <y_um> <parent> <arr_max> <arr_min>        die clock cell (buffer/inverter/ICG), node = its output pin
#   T <node> <master> <x_um> <y_um> <parent> <arr_max> <arr_min>      tile (block instance) clock entry pin
#   F <node> <cell> <x_um> <y_um> <parent> <arr_max> <arr_min>        die-level sequential cell clock pin
#   P <instA> <instB> <net>                                         two tiles sharing a data net
#   S <key> <value>                                                 summary counters
# arr_* are OpenSTA pin arrivals (arrival_max_rise / arrival_min_rise, the session's time unit: ps on ASAP7); "-" = none.

proc dcc_env {n d} { if {[info exists ::env($n)] && $::env($n) ne ""} { return $::env($n) }; return $d }

proc dcc_xy {obj} {
  set r [$obj getBBox]
  set dbu $::dcc_dbu
  return [list [format %.3f [expr {([$r xMin] + [$r xMax]) / 2.0 / $dbu}]] [format %.3f [expr {([$r yMin] + [$r yMax]) / 2.0 / $dbu}]]]
}

proc dcc_arr {name {port 0}} {
  if {!$::dcc_sta} { return [list - -] }
  set esc [string map {[ \\[ ] \\]} $name]
  if {$port} { set p [get_ports -quiet $esc] } else { set p [get_pins -quiet $esc] }
  if {$p eq ""} { return [list - -] }
  set out {}
  foreach prop {arrival_max_rise arrival_min_rise} {
    if {[catch {set v [get_property $p $prop]}] || $v eq "" || $v eq "INF" || $v eq "-INF"} { lappend out - } else { lappend out $v }
  }
  return $out
}

proc dcc_seq {cell} { return [regexp {(?i)DFF|DHL|DLL|SDF|LATCH} $cell] }

# Walk every load of a clock net.  parent = the node that drives this net.
proc dcc_walk {net parent} {
  if {[dict exists $::dcc_seen_net [$net getName]]} { return }
  dict set ::dcc_seen_net [$net getName] 1
  incr ::dcc_nets
  foreach it [$net getITerms] {
    set mt [$it getMTerm]
    if {[$mt getIoType] ne "INPUT"} { continue }
    set inst [$it getInst]; set m [$inst getMaster]
    set iname [$inst getName]; set pin "$iname/[$mt getName]"
    lassign [dcc_xy $it] x y
    if {[$m isBlock]} {
      lassign [dcc_arr $pin] amax amin
      puts $::dcc_fh [join [list T $pin [$m getName] $x $y $parent $amax $amin] "\t"]
      incr ::dcc_tiles
      continue
    }
    if {[dcc_seq [$m getName]]} {
      lassign [dcc_arr $pin] amax amin
      puts $::dcc_fh [join [list F $pin [$m getName] $x $y $parent $amax $amin] "\t"]
      incr ::dcc_flops
      continue
    }
    if {[dict exists $::dcc_seen_inst $iname]} { continue }
    dict set ::dcc_seen_inst $iname 1
    # pass-through clock cell (buffer, inverter, clock gate, delay cell): continue on each driven output net
    foreach ot [$inst getITerms] {
      if {[[$ot getMTerm] getIoType] ne "OUTPUT"} { continue }
      set on [$ot getNet]
      if {$on eq "NULL" || $on eq ""} { continue }
      set opin "$iname/[[$ot getMTerm] getName]"
      lassign [dcc_xy $inst] bx by
      lassign [dcc_arr $opin] amax amin
      puts $::dcc_fh [join [list B $opin [$m getName] $bx $by $parent $amax $amin] "\t"]
      incr ::dcc_bufs
      dcc_walk $on $opin
    }
  }
}

proc die_clock_check {} {
  set out [dcc_env OT_DCC_OUT ""]
  if {$out eq ""} { error "die_clock_check: set ::env(OT_DCC_OUT)" }
  set blk [ord::get_db_block]
  set ::dcc_dbu [$blk getDbUnitsPerMicron]
  set ::dcc_sta [dcc_env OT_DCC_STA 1]
  set ::dcc_seen_net [dict create]; set ::dcc_seen_inst [dict create]
  set ::dcc_nets 0; set ::dcc_tiles 0; set ::dcc_flops 0; set ::dcc_bufs 0
  if {$::dcc_sta} {
    # build the timing graph before reading pin properties (pinArrival on an un-graphed pin can crash)
    catch { sta::find_timing_paths -path_delay max -group_path_count 1 }
  }
  set roots [dcc_env OT_DCC_ROOTS ""]
  if {$roots eq ""} {
    foreach clk [all_clocks] {
      foreach src [get_property $clk sources] { lappend roots [get_full_name $src] }
    }
  }
  set ::dcc_fh [open $out w]
  set nroots 0
  foreach r [lsort -unique $roots] {
    set bt [$blk findBTerm $r]
    if {$bt ne "NULL" && $bt ne ""} {
      set net [$bt getNet]; set node "port:$r"; lassign [dcc_xy $bt] x y; lassign [dcc_arr $r 1] amax amin
    } else {
      set it [$blk findITerm $r]
      if {$it eq "NULL" || $it eq ""} { puts "DIE_CLOCK_CHECK root $r not in the db (skipped)"; continue }
      set net [$it getNet]; set node $r; lassign [dcc_xy $it] x y; lassign [dcc_arr $r] amax amin
    }
    if {$net eq "NULL" || $net eq ""} { continue }
    puts $::dcc_fh [join [list R $node $x $y $amax $amin] "\t"]
    incr nroots
    dcc_walk $net $node
  }
  # tile pairs that exchange data: a signal net (not in the clock network) joining 2..MAX_FANOUT tile instances
  set maxf [dcc_env OT_DCC_MAX_FANOUT 8]
  set npairs 0; set nbroad 0
  foreach net [$blk getNets] {
    if {[$net getSigType] ne "SIGNAL" || [dict exists $::dcc_seen_net [$net getName]]} { continue }
    set tiles {}
    foreach it [$net getITerms] {
      set inst [$it getInst]
      if {[[$inst getMaster] isBlock]} { lappend tiles [$inst getName] }
    }
    set tiles [lsort -unique $tiles]
    set n [llength $tiles]
    if {$n < 2} { continue }
    if {$n > $maxf} { incr nbroad; continue }
    for {set i 0} {$i < $n} {incr i} {
      for {set j [expr {$i + 1}]} {$j < $n} {incr j} {
        set k "[lindex $tiles $i]\t[lindex $tiles $j]"
        if {![info exists seen($k)]} { set seen($k) 1; puts $::dcc_fh "P\t$k\t[$net getName]"; incr npairs }
      }
    }
  }
  foreach {k v} [list roots $nroots clock_nets $::dcc_nets clock_cells $::dcc_bufs tile_entries $::dcc_tiles \
                     die_flops $::dcc_flops tile_pairs $npairs broadcast_nets_skipped $nbroad max_fanout $maxf sta $::dcc_sta] {
    puts $::dcc_fh "S\t$k\t$v"
  }
  close $::dcc_fh
  puts "DIE_CLOCK_CHECK roots $nroots clock_cells $::dcc_bufs tile_entries $::dcc_tiles die_flops $::dcc_flops tile_pairs $npairs -> $out"
}

die_clock_check
