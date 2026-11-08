import sys,pathlib,json
k=pathlib.Path(sys.argv[1]);p=k/'rck_tx_compact.tcl';s=p.read_text()
a=s.index('set ::env(OT_TAP_GROUP_RE)');b=s.index('proc rck_clean')
s=s[:a]+r'''# S81-RCK-6 11-07 vH.  Raw ODB names carry backslashes (pin_q\[0\]\[7\]$_DFF_P_): the vG regex had none, so no pin row grouped.
# pin_v / pin_rst_n are one merged FF per stage with D = rs_t[1]: no timing path to data in stages 0 and 1, so only pin_v[2] joins a group, the encoder's.
# Each pin_q stage is its own whole-row group on its centroid's tap; the encoder tree keeps its 200 um span.
set ::env(OT_TAP_GROUP_RE) {(u_core\.u_tx_pin\.u_enc|u_bin_coll_i0|u_cland_coll_i0|u_core\.u_tx_pin\.pin_q\\?\[[0-2]\\?\]|u_core\.u_tx_pin\.pin_v\\?\[2\\?\])}
set ::env(OT_TAP_GROUP_ALIAS) [list u_core.u_tx_pin.u_enc=encoder u_core.u_tx_pin.pin_v*=encoder u_bin_coll_i0=coll_capture u_cland_coll_i0=coll_capture]
'''+s[b:]
s+=r'''
# S81-RCK-6 11-07 vH: the reset/valid chain follows its own source: evenly from rs_t[1] to the encoder box north wall.  vG hops 447/50/441 um, v2 outside the fence.
proc rck_tx_pose_controls {} {
  set b [ord::get_db_block]; set u [$b getDbUnitsPerMicron]; set src ""; set v [dict create]
  foreach i [$b getInsts] {
    if {![rck_ff $i]} continue
    set n [rck_clean [$i getName]]
    if {[regexp {u_core[./]rs_t\[1\]} $n]} {set src $i}
    if {[regexp {u_core[./]u_tx_pin[./]pin_v\[([0-2])\]} $n -> j]} {dict set v $j $i}
  }
  if {$src eq "" || [dict size $v] != 3} {error "RCK_TX_CONTROL: selector found src='$src' stages=[dict size $v]"}
  lassign [$src getLocation] px py
  set tx [expr {round(2165*$u)}]; set ty [expr {round(462*$u)}]
  foreach j {0 1 2} {
    set f [expr {($j+1)/3.0}]; set x [expr {round($px+($tx-$px)*$f)}]; set y [expr {round($py+($ty-$py)*$f)}]
    set i [dict get $v $j]; $i setLocation $x $y; $i setPlacementStatus PLACED
    # the QN inverter goes with its flop; deeper encoder reset buffers stay where they serve
    set moved 0
    foreach o [$i getITerms] {
      if {![$o isOutputSignal] || [$o getNet] eq "NULL"} continue
      foreach l [[$o getNet] getITerms] {
        if {![$l isInputSignal]} continue
        set li [$l getInst]
        if {[regexp {^(BUF|INV)} [[$li getMaster] getName]]} {$li setLocation [expr {$x+round(2*$u)}] $y; $li setPlacementStatus PLACED; incr moved}
      }
    }
    puts "RCK_TX_CONTROL pin_v$j at [expr {double($x)/$u}] [expr {double($y)/$u}] moved_inverters $moved"
  }
}
# Fail closed: a silent alias miss cost one whole vG place.
proc rck_tx_assert_cohort {} {
  set b [ord::get_db_block]; set u [$b getDbUnitsPerMicron]; set nets [dict create]
  foreach i [$b getInsts] {
    if {![rck_ff $i]} continue
    set n [rck_clean [$i getName]]; set k ""
    if {[regexp {u_core[./]u_tx_pin[./]pin_q\[([0-2])\]} $n -> j]} {set k pin$j
    } elseif {[regexp {u_core[./]u_tx_pin[./]pin_v\[2\]} $n] || [regexp {u_core[./]u_tx_pin[./]u_enc[./]} $n]} {set k encoder
    } elseif {[regexp {u_bin_coll_i0[./]} $n]} {set k bin}
    if {$k eq ""} continue
    foreach t [$i getITerms] {if {[[$t getMTerm] getName] eq "CLK"} {dict incr nets "$k [[$t getNet] getName]"}}
  }
  puts "RCK_TX_COHORT $nets"
  set seen [dict create]; dict for {kn c} $nets {dict incr seen [lindex $kn 0]}
  foreach k {pin0 pin1 pin2 encoder bin} {if {![dict exists $seen $k] || [dict get $seen $k] != 1} {error "RCK_TX_COHORT $k not on one tap: $nets"}}
}
'''
p.write_text(s)
p=k/'rck_tx_pre_detail_place_tcl.tcl';s=p.read_text()
n='source /work/chain_even.tcl\nsource /work/clock_taps.tcl\n'
assert s.count(n)==1
s=s.replace(n,'source /work/chain_even.tcl\nrck_tx_pose_controls\nsource /work/clock_taps.tcl\nrck_tx_assert_cohort\n')
p.write_text(s)
j=json.load(open(k/'SOURCE_PROFILE.json'))
j['prototype']=str(k);j['goal']='place then cts, stage resume on vG 3_4'
j['changes']+=['S81-RCK-6 vH: group regex matches raw escaped names; one whole-row tap group per pin_q stage','S81-RCK-6 vH: pin_v chain posed evenly rs_t[1] to encoder north wall; pin_v[2] on encoder tap','S81-RCK-6 vH: exact export reuse 583a134100 landing_exports.tcl','S81-RCK-6 vH: fail-closed cohort check after tap assignment']
json.dump(j,open(k/'SOURCE_PROFILE.json','w'),indent=2)
