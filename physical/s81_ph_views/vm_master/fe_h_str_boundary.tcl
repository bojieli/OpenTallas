# el1013-s81-vmfe/B6: two-clock boundary + inter-clock insertion balance of the FE leaves dsfd_vm_fcc / dsfd_vm_fcn
# (spec "boundary_tcl"; the dsfd_vm_be_sl method, be_sl_str_boundary.tcl r4, made two-sided and name-driven).
#  * the ref_tile io_ref switch unsets every IO delay and re-times all ports against core_clk at 166.667 ps: after it the
#    two-clock boundary fe_h_str_clock_ref.sdc is re-read (stream ports on str_clk, each domain on its own tree).
#    PRE_CTS: wraps clock_tree_synthesis after the io_ref wrapper; PRE_GLOBAL_ROUTE / POST_DETAIL_ROUTE: directly.
#  * ck (1,111.1 ps) and cks (833.3 ps) are one 4 : 3 pair from one die PLL root and the tile must show ONE insertion on
#    both (the die delivers each clock pin at phi - R): TritonCTS builds the two trees independently, so right after CTS a
#    dont_touch BUFx12f chain is spliced behind the EARLIER clock's port until the mean insertion of the CROSSING flops
#    (pointer / state hops and storage hops weighted equally) is within one stage of the other's.
set ::ot_feh_sdc [file join [file dirname [info script]] fe_h_str_clock_ref.sdc]
proc ot_feh_boundary {} {
  catch {estimate_parasitics -placement}
  read_sdc $::ot_feh_sdc
  puts "FE_H two-clock boundary re-applied after the io_ref switch"
}
proc ot_feh_ins_mean {clk} {
  catch {sta::worst_slack_cmd max}
  # B8: the crossings are real two-clock CDCs now (Gray pointers / storage read after the pointer: max-delay arcs, see
  # fe_h_str_clock_ref.sdc); the balance only serves the few arcs that stay timed between the related clocks (sticky
  # status levels) and the tile's ONE insertion figure: reference = the engine adapter's two sides (fcn), else all registers
  set ptr {^$}; set sto {^$}
  set sp 0.0; set np 0; set ss 0.0; set ns 0; set sa 0.0; set na 0; set sx 0.0; set nx 0
  foreach p [all_registers -clock $clk -clock_pins] {
    set a [get_property $p arrival_max_rise]
    if {![string is double -strict $a] || abs($a) >= 1e5} { continue }
    set sa [expr {$sa + $a}]; incr na
    set nm [get_full_name $p]
    if {[regexp $ptr $nm]} { set sp [expr {$sp + $a}]; incr np } elseif {[regexp $sto $nm]} { set ss [expr {$ss + $a}]; incr ns
    } elseif {[regexp {u_ad\.} $nm]} { set sx [expr {$sx + $a}]; incr nx }    ;# dsfd_vm_fcn: the engine adapter's two sides
  }
  if {$na == 0} { return "" }
  if {$np > 0 && $ns > 0} {
    puts [format "FE_H clk balance ref %s: crossing pointer %.1f (n %d) storage %.1f (n %d) all %.1f (n %d)" $clk [expr {$sp/$np}] $np [expr {$ss/$ns}] $ns [expr {$sa/$na}] $na]
    return [expr {0.5 * ($sp / $np + $ss / $ns)}]
  }
  if {$nx > 0} {
    puts [format "FE_H clk balance ref %s: engine adapter %.1f (n %d) all %.1f (n %d)" $clk [expr {$sx/$nx}] $nx [expr {$sa/$na}] $na]
    return [expr {$sx / $nx}]
  }
  puts "FE_H clk balance ref $clk: no crossing flops matched; all-register mean"
  return [expr {$sa / $na}]
}
proc ot_feh_clk_balance {} {
  set blk [ord::get_db_block]; set db [ord::get_db]
  set m [$db findMaster BUFx12f_ASAP7_75t_R]
  if {$m eq "NULL"} { puts "FE_H clk balance: no BUFx12f master; skipped"; return }
  catch {set_propagated_clock [all_clocks]}
  set k 0; set dir 0; set port ""
  for {set it 0} {$it < 32} {incr it} {
    catch {estimate_parasitics -placement}
    set lc [ot_feh_ins_mean core_clk]; set ls [ot_feh_ins_mean str_clk]
    if {$lc eq "" || $ls eq ""} { puts "FE_H clk balance: no insertion (core '$lc' str '$ls'); skipped"; return }
    set d [expr {$lc - $ls}]
    puts [format "FE_H clk balance it %d: core_clk %.1f ps str_clk %.1f ps (core - str %.1f, %d chain cells on '%s')" $it $lc $ls $d $k $port]
    if {$dir == 0} {
      if {abs($d) <= 7.0} break
      set dir [expr {$d > 0 ? 1 : -1}]; set port [expr {$dir > 0 ? "cks" : "ck"}]     ;# delay the EARLIER clock
    }
    if {$dir * $d <= 0} break
    set bt [$blk findBTerm $port]
    if {$bt eq "NULL"} { set bt [$blk findBTerm "${port}\[0\]"] }
    if {$bt eq "NULL" || [$bt getNet] eq "NULL"} { puts "FE_H clk balance: no $port port net; skipped"; return }
    set n0 [$bt getNet]
    set loads {}
    foreach l [$n0 getITerms] { lappend loads $l }
    if {![llength $loads]} { puts "FE_H clk balance: $port net has no loads"; return }
    lassign [[[lindex $loads 0] getInst] getLocation] x y
    set c [odb::dbInst_create $blk $m "ot_feh_${port}bal_$k"]
    set n1 [odb::dbNet_create $blk "ot_feh_${port}bal_n$k"]
    $n1 setSigType CLOCK
    set ndt 0
    catch {set ndt [$n0 isDoNotTouch]}
    if {$ndt} { $n0 setDoNotTouch 0 }
    foreach l $loads {
      set li [$l getInst]; set dt 0
      catch {set dt [$li isDoNotTouch]}
      if {$dt} { $li setDoNotTouch 0 }
      $l disconnect; $l connect $n1
      if {$dt} { $li setDoNotTouch 1 }
    }
    [$c findITerm A] connect $n0
    [$c findITerm Y] connect $n1
    if {$ndt} { $n0 setDoNotTouch 1; $n1 setDoNotTouch 1 }
    $c setLocation $x $y
    $c setPlacementStatus PLACED
    catch {$c setDoNotTouch 1}
    incr k
  }
  puts [format "FE_H clk balance done: %d chain cells on '%s', core_clk %.1f str_clk %.1f" $k $port $lc $ls]
}
if {[llength [info commands ::qdm_cts_orig]] && ![llength [info commands ::ot_feh_cts_inner]]} {
  rename clock_tree_synthesis ::ot_feh_cts_inner
  proc clock_tree_synthesis {args} {
    ::ot_feh_cts_inner {*}$args
    if {![info exists ::env(OT_FEH_BAL)] || $::env(OT_FEH_BAL) ne "0"} { ot_feh_clk_balance }
    ot_feh_boundary
  }
} else {
  ot_feh_boundary
}
