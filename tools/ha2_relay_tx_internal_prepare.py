#!/usr/bin/env python3
"""Emit the pin contract for the internal-only local launch/TX experiment."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'physical/ha2_relay_tx_internal_20261007'
def pins():
 out=[]
 for lane,start in enumerate((160.044,580.044)):
  groups=[('S',[f'arrival_v[{lane}]']+[f'arrival_data[{lane*544+i}]' for i in range(544)]),
          ('N',[f'send_v[{lane}]']+[f'send_data[{lane*544+i}]' for i in range(544)]+[f'send_tag[{lane*16+i}]' for i in range(16)])]
  for face,names in groups:
   for i,name in enumerate(names):out.append(dict(name=name,face=face,layer='M5',x=round(start+i*.144,6),y=.042 if face=='S' else 40.134))
 ret=[f'return_v[{l}]' for l in range(2)]+[f'return_tag[{i}]' for i in range(32)]
 ctl=['clk','rst_n','quiet','fault','issue_v[0]','issue_v[1]','issue_ready[0]','issue_ready[1]']
 for face,names in [('E',ret),('W',ctl)]:
  for i,name in enumerate(names):out.append(dict(name=name,face=face,layer='M4',x=839.982 if face=='E' else .042,y=round(10.044+i*.144,6)))
 assert len(out)==2254 and len({p['name'] for p in out})==2254
 return out

def main():
 ps=pins();HERE.mkdir(exist_ok=True,parents=True)
 (HERE/'pins.json').write_text(json.dumps(ps,indent=2)+'\n')
 (HERE/'pins.tcl').write_text('# Full physical pin contract, internal-only timing vehicle.\n'+'\n'.join('place_pin -pin_name {%s} -layer %s -location {%.6f %.6f}'%(p['name'],p['layer'],p['x'],p['y']) for p in ps)+'\n')
 text=['set b [ord::get_db_block]','set dbu [$b getDbUnitsPerMicron]','set expected {']
 for p in ps:text.append(' {{%s} %s %.6f}'%(p['name'],p['face'],p['x'] if p['face'] in ('N','S') else p['y']))
 text+=['}']
 text+=r'''
set checked 0
foreach row $expected {
 lassign $row name face coord
 set t [$b findBTerm $name]
 if {$t eq "NULL"} {error "missing signal pin $name"}
 set match 0
 foreach p [$t getBPins] {foreach box [$p getBoxes] {
  set xl [expr {[$box xMin]/double($dbu)}];set xh [expr {[$box xMax]/double($dbu)}]
  set yl [expr {[$box yMin]/double($dbu)}];set yh [expr {[$box yMax]/double($dbu)}]
  set lay [[$box getTechLayer] getName]
  if {$face eq "N" || $face eq "S"} {
   set got [expr {($xl+$xh)/2.}];set edge [expr {$face eq "N" ? abs($yh-40.176):abs($yl)}]
   set width [expr {$xh-$xl}];set depth [expr {$yh-$yl}];set expected_layer M5
  } else {
   set got [expr {($yl+$yh)/2.}];set edge [expr {$face eq "E" ? abs($xh-840.024):abs($xl)}]
   set width [expr {$yh-$yl}];set depth [expr {$xh-$xl}];set expected_layer M4
  }
  set tr [expr {($got-.012)/.048}]
  if {abs($got-$coord)<.0011 && $edge<.0011 && $lay eq $expected_layer && abs($width-.024)<.0011 && abs($depth-.084)<.0011 && abs($tr-round($tr))<.0011} {set match 1}
 }}
 if {!$match} {error "pin moved/wrong native geometry $name"}
 incr checked
}
set signals 0
foreach t [$b getBTerms] {
 if {[$t getSigType] ni {POWER GROUND}} {incr signals}
}
if {$signals!=2254 || $checked!=2254} {error "unexpected signal count $signals checked $checked"}
puts "HA2_RELAY_TX_PINS_PASS checked=$checked signal_count=$signals"
'''.strip().splitlines()
 (HERE/'check_pins.tcl').write_text('\n'.join(text)+'\n')
if __name__=='__main__':main()
