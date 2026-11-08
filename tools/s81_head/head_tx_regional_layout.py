#!/usr/bin/env python3
"""HEAD TX regional form: local CH capture and delay/PMA clock groups, zero new cycles.

Create clock groups and a pre-place hook in a private kit. The physical pilot must
inspect new CH mux reach too: replication moves that shared source upstream.
"""
import argparse,json,re
from pathlib import Path

def write(kit):
    kit=Path(kit); groups=json.loads((kit/'clock_atomic_groups.json').read_text())
    old={g['name']:g['members'] for g in groups['groups']};new=[]
    for bit in range(512):
        members=old[f'enc_{bit}']
        new.append(dict(name=f'in_{bit}',members=members[:1]))
        new.append(dict(name=f'data_pma_{bit}',members=members[1:]+old[f'ptx_{bit}']))
    new.extend(dict(name=f'ptx_{i}',members=old[f'ptx_{i}']) for i in range(512,544))
    # Each eight-bit region group has exactly sixteen sinks: capture + cq.
    for r in range(4):
        for k in range(65):
            members=[]
            for bit in range(k*8,k*8+8):
                for root in ('g_ch_region.mid','g_ff.cq'):
                    members.append(f'u_enc.{root}\\[{r}\\]\\[{bit}\\]$_DFF_P_')
            new.append(dict(name=f'ch_r{r}_{k}',members=members))
    groups['groups']=new
    (kit/'clock_atomic_groups.json').write_text(json.dumps(groups,indent=1)+'\n')
    (kit/'clock_atomic_groups.tcl').write_text('\n'.join('{'+g['name']+' {'+' '.join('{'+m+'}' for m in g['members'])+'}}' for g in new)+'\n')
    (kit/'atomic_guides_place.tcl').write_text(TCL)

TCL=r'''# Source form codex/head-tx-regional: no GPL regions; anchors released at DPL.
source /work/face_flops.tcl
uplevel #0 {
set b [ord::get_db_block]
set u [[ord::get_db_tech] getDbUnitsPerMicron]
set rows [$b getRows]
set core [$b getCoreArea]
set sw [[[lindex $rows 0] getSite] getWidth]
set count 0
set out [open $::env(RESULTS_DIR)/ot_face_flops.txt a]
foreach inst [$b getInsts] {
  set nm [string map [list "\\" ""] [$inst getName]]
  set xy {}
  if {[regexp {^u_enc\.(g_ch_region\.mid|g_ff\.cq)\[([0-3])\]\[([0-9]+)\]} $nm -> bank r bit]} {
    # Four parity regions; pair each retained capture with its own cq sink.
    set x [expr {32 + 112*$r + 1.15*($bit%65)}]
    set y [expr {24 + 9*int($bit/65) + ($bank eq "g_ff.cq" ? 0.54 : 0)}]
    set xy [list $x $y]
  } elseif {[regexp {^u_enc\.d([1-8])\[([0-9]+)\]} $nm -> stage bit]} {
    # Input d0 stays on the input face. Internal delay chain follows its PMA slice.
    set xy [list [expr {238.68 + .288*$bit}] [expr {10 + 4*($bit%4) + .27*($stage-1)}]]
  } elseif {[regexp {^u_enc\.p_d\[([0-9]+)\]} $nm -> bit]} {
    set xy [list [expr {238.68 + .288*$bit}] [expr {10 + 4*($bit%4) + 8*.27}]]
  } elseif {[regexp {^u_ptx\.l\[([01])\]\[([0-9]+)\]} $nm -> stage bit]} {
    set xy [list [expr {238.68 + .288*$bit}] [expr {10 + 4*($bit%4) + (9+$stage)*.27}]]
  }
  if {![llength $xy] || ![string match "*DFF*" [[$inst getMaster] getName]]} continue
  set xx [expr {round(([lindex $xy 0]*$u-[$core xMin])/double($sw))*$sw+[$core xMin]}]
  set target [expr {[lindex $xy 1]*$u}]
  set best ""; set delta 1e30
  foreach row $rows {
    set y [lindex [$row getOrigin] 1]
    if {abs($y-$target)<$delta} {set best $row;set delta [expr {abs($y-$target)}]}
  }
  if {[$inst getPlacementStatus] in {FIXED LOCKED COVER}} {error "REGIONAL user fixed $nm"}
  $inst setPlacementStatus PLACED
  $inst setOrient [$best getOrient]
  $inst setLocation $xx [lindex [$best getOrigin] 1]
  $inst setPlacementStatus FIRM
  puts $out "[$inst getName]\tREGIONAL\t[expr {$xx/double($u)}]\t[expr {[lindex [$best getOrigin] 1]/double($u)}]\tregion_capture_or_pma"
  incr count
}
close $out
puts "OT_TX_REGIONAL firm $count members; input/output face flops preserved"
if {$count<8000} {error "REGIONAL expected retained regional and data banks, got $count"}
}
'''

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('kit');a=p.parse_args();write(a.kit)
