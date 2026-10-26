"""Candidate D-S81-B2 engine pin reassignment; zero RTL/cycle changes.
Never changes a canonical plan: emits a trial pin table and placement hooks.
"""
import argparse, collections, json, re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('kit',type=Path);a=p.parse_args();k=a.kit
pins=json.loads((k/'pins.json').read_text());assert len(pins)==2690
counts=collections.Counter(q['bus'] for q in pins)
assert {b:counts[b] for b in ['pci','f_ks','st','rco']}=={'pci':264,'f_ks':53,'st':4,'rco':39}
starts={'pci':4.812,'rco':90.012,'f_ks':180.012,'st':240.012,'cfg_en':80.028,'cfg_layer':81.036,'cfg_rank':82.044}
changes=[]
for q in pins:
 if q['bus'] in starts:
  old=dict(q);q.update(face='W',layer='M4',x=.042,y=round(starts[q['bus']]+.24*(q['bit'] or 0),6));changes.append({'old':old,'new':q.copy()})
locs=[(q['layer'],q['x'],q['y']) for q in pins];assert len(locs)==len(set(locs)), 'pin collision'
(k/'pins.json').write_text(json.dumps(pins,indent=2)+'\n')
lines=['# CANDIDATE D-S81-B2: land input buses beside their actual macro consumers.']
for q in pins:
 n=q['bus']+(f"[{q['bit']}]" if counts[q['bus']]>1 else '')
 size='0.0840 0.0240' if q['layer'] in ['M4','M6'] else '0.0240 0.0840'
 lines.append(f"place_pin -pin_name {{{n}}} -layer {q['layer']} -location {{{q['x']:.4f} {q['y']:.4f}}} -pin_size {{{size}}}")
(k/'io.tcl').write_text('\n'.join(lines)+'\n')
(k/'eng_reach_delta.json').write_text(json.dumps({'status':'PROPOSED_TRIAL_ONLY','rtl_changes':0,'cycle_delta':0,'changes':changes},indent=2)+'\n')
hook='''# Zero-cycle reset-leaf placement: keep the existing third release edge.
set er_b [ord::get_db_block]
set er_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set er_n 0
foreach er_i [$er_b getInsts] {
 if {[string match {*u_r.g_tleaf[[]0[]].q*} [$er_i getName]]} {
  $er_i setLocation [expr {round(180.0*$er_dbu)}] [expr {round(240.0*$er_dbu)}]
  $er_i setPlacementStatus FIRM
  incr er_n
 }
}
if {$er_n != 1} {error "eng reach: expected exactly one reset leaf0, got $er_n"}
puts "ENG_REACH reset leaf0 placed at180,240 without adding an edge"
'''
(k/'eng_reach.tcl').write_text(hook)
with (k/'gpl_hooks.tcl').open('a') as f:f.write('\nsource /work/eng_reach.tcl\n')
print('CANDIDATE',len(changes),'pins moved; existing reset leaf0 centered; zero RTL/cycle changes')
