# QC-TTCTLM-1119 form (b): early clock for ROM macros whose read data ends are the type's worst TT setup ends
# (tt_ctlm r1b CTS: calendar m1 rd_out -> fault -106.1 ps, ROM access 591 ps; leaf op ROM rd_out -> h_good_q -50.7,
# access 520 ps), while their address / ce inputs keep 176-652 ps of setup slack.  POST_CTS hook, opt-in:
#   OT_ROM_EARLY = "<instance glob>:<advance ps> ..."   e.g. "*g_calrom.u_rom.m?:160 *u_leaf.g_op*u_rom*:110"
# For each matching macro instance the clk pin is moved, with no new cell, from its leaf net to the first net up its
# own clock trunk (same tap, same root) whose STA arrival is at least <advance> earlier, keeping the polarity (an
# inverter stage is only crossed in pairs).  Prints OT_ROM_EARLY lines (instance, from net, to net, arrival before /
# after, input setup slack before the move).  Nothing else changes; the kit's TT repair / measure / hold gates follow.
proc ot_rom_early_arr {pinname} {
  set p [get_pins -quiet $pinname]
  if {![llength $p]} { return "" }
  set a [get_property $p arrival_max_rise]
  if {$a eq "" || $a eq "INF" || $a eq "-INF"} { return "" }
  return $a
}
proc ot_rom_early_apply {spec} {
  set block [ord::get_db_block]
  catch { estimate_parasitics -placement }
  foreach item $spec {
    set k [string last ":" $item]
    set pat [string range $item 0 [expr {$k - 1}]]; set adv [string range $item [expr {$k + 1}] end]
    set n 0
    foreach inst [$block getInsts] {
      set name [$inst getName]
      if {![string match $pat $name]} continue
      if {![[$inst getMaster] isBlock]} continue
      set it [$inst findITerm clk]
      if {$it eq "NULL" || $it eq ""} { puts "OT_ROM_EARLY $name SKIP no clk pin"; continue }
      set net0 [$it getNet]
      set a0 [ot_rom_early_arr "$name/clk"]
      set cur $net0; set inv 0; set chosen ""; set achosen ""
      for {set lvl 0} {$lvl < 16} {incr lvl} {
        set drv ""
        foreach t [$cur getITerms] { if {[$t isOutputSignal]} { set drv $t; break } }
        if {$drv eq ""} break
        set dinst [$drv getInst]; set mname [[$dinst getMaster] getName]
        if {![regexp {^(BUF|INV|CKINV|CKBUF|HB)} $mname]} break
        if {[string match INV* $mname] || [string match CKINV* $mname]} { set inv [expr {1 - $inv}] }
        set inp ""
        foreach t [$dinst getITerms] { if {[$t isInputSignal] && [$t getNet] ne "NULL"} { set inp $t; break } }
        if {$inp eq ""} break
        set up [$inp getNet]
        set au [ot_rom_early_arr "[$dinst getName]/[[$inp getMTerm] getName]"]
        if {$inv == 0 && $au ne "" && $a0 ne "" && ($a0 - $au) >= $adv} { set chosen $up; set achosen $au; break }
        set cur $up
      }
      if {$chosen eq ""} { puts "OT_ROM_EARLY $name SKIP no trunk net >= $adv ps earlier (arrival $a0)"; continue }
      $it disconnect
      $it connect $chosen
      incr n
      puts [format "OT_ROM_EARLY %s from %s to %s arrival %.1f -> %.1f (advance %.1f, target %s)" $name [$net0 getName] [$chosen getName] $a0 $achosen [expr {$a0 - $achosen}] $adv]
    }
    puts "OT_ROM_EARLY pattern $pat moved $n"
  }
  catch { estimate_parasitics -placement }
}
if {[info exists ::env(OT_ROM_EARLY)] && [string trim $::env(OT_ROM_EARLY)] ne ""} { ot_rom_early_apply $::env(OT_ROM_EARLY) }
