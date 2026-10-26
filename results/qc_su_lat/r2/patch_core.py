# QC-SU-LAT-R2: opt-in OT_MSCTS_EXPLICIT (stage buffers at the spec points: identical chains by construction) and
# OT_MSCTS_ENTRY_CELLS (designed fixed entry delay between the ck pin and the root, same chain per type). Defaults unchanged.
import sys
p=sys.argv[1]; t=open(p).read()
a="""  set rnet [ot_ms_mk_net ot_ms_root_n]
  set r [ot_ms_mk_inst ot_ms_root $rcell $rx $ry]; ot_ms_conn $r $pnet $rnet
"""
b="""  set ot_ms_ex [ot_ms_env OT_MSCTS_EXPLICIT 0]
  if {$ot_ms_ex} {
    set N [expr {[llength [lindex [lindex $taps 0] 1]] / 2 - 1}]
    foreach t $taps { if {[llength [lindex $t 1]] / 2 - 1 != $N} { error "OT_MSCTS_EXPLICIT: tap [lindex $t 0] stage count differs from $N" } }
  }
  set ne [ot_ms_env OT_MSCTS_ENTRY_CELLS 0]; set ecell [ot_ms_env OT_MSCTS_ENTRY_CELL BUFx4_ASAP7_75t_R]; set inet $pnet
  for {set j 1} {$j <= $ne} {incr j} {
    set en [ot_ms_mk_net ot_ms_entry${j}_n]; set eb [ot_ms_mk_inst ot_ms_entry$j $ecell [expr {$rx - 1.2 * ($ne - $j + 1)}] $ry]; ot_ms_conn $eb $inet $en; set inet $en
  }
  if {$ne} { puts "OT_MSCTS_BUILD entry chain $ne x $ecell (designed fixed entry delay)" }
  set rnet [ot_ms_mk_net ot_ms_root_n]
  set r [ot_ms_mk_inst ot_ms_root $rcell $rx $ry]; ot_ms_conn $r $inet $rnet
"""
c="""      lassign [ot_ms_free_pt {*}[ot_ms_at $pts [expr {$k * $s}]] $rects] x y
"""
d="""      if {$ot_ms_ex} { set x [lindex $pts [expr {2 * $k}]]; set y [lindex $pts [expr {2 * $k + 1}]] } else { lassign [ot_ms_free_pt {*}[ot_ms_at $pts [expr {$k * $s}]] $rects] x y }
"""
assert t.count(a)==1 and t.count(c)==1
t=t.replace(a,b).replace(c,d); open(p,'w').write(t); print('patched',p)
