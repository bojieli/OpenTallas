#!/usr/bin/env python3
"""Assign count-leaf faces from gather root tap locations and the staged return lane.
One common master per NR. Average the root tap x over its repeated placements;
use per-root bit order at the N face, E/W registered live chain, S return/clock.
"""
import json
from pathlib import Path
import v19_pins_1014 as V
ROOT=Path(__file__).resolve().parents[2]

def main():
 out=ROOT/'physical/s81_die_pins/v20'
 out.mkdir(exist_ok=True)
 slots=json.loads((ROOT/'physical/s81_die_pins/v19/pq_count_slots.json').read_text())
 gx=slots['geometry']['gather_slot'][0]
 for nr in (15,2):
  ss=[s for s in slots['slots'] if s['nr']==nr]
  ports={'r_v':[], 'r_tag':[], 'r_e':[]}
  for k in range(nr):
   c=sum(sum(s['n_face_taps'][k]['x_um'])/2 - (s['at_die'][0]-gx) for s in ss)/len(ss)
   c=max(1.0,min(134.0,c))
   ports['r_v'].append(['N','M5',round(c,3),.192])
   ports['r_tag'] += [['N','M5',round(c+.096*i,3),.192] for i in (1,2)]
   ports['r_e'].append(['N','M5',round(c+.288,3),.192])
  ports['g_flt']=[['N','M5',141.12,.192]]
  ports['live']=[['E','M4',8.64+.144*i,.192] for i in range(4)]
  ports['live_o']=[['W','M4',8.64+.144*i,.192] for i in range(4)]
  ports['ga']=[['S','M5',70.128+.144*i,.192] for i in range(16)]
  ports['q2f']=[['S','M5',72.432,.192]]
  ports['clk']=[['S','M5',4.32,.192]]
  ports['rst_n']=[['S','M5',8.64,.192]]
  V.write(out,'ot_s81_pq_rwbc'+str(nr),[142.56,19.44],ports,'clk',
    'N tap positions from gather root x, averaged across same-master placements; S staged return corridor; live chain E->W',
    'v20_pq_count_seam',{'source':'tools/s81/pq_count_pins.py', 'adoption':'OFF until composed live epoch/flight proof and die hop screen pass'})
 for s in slots['slots']:s['outline'][1]=19.44
 slots['case']='v20_pq_count_seam';slots['geometry']['live']='live[3:0] registered E->W leaf chain; epoch/flight exact proof required'
 (out/'pq_count_slots.json').write_text(json.dumps(slots,indent=1)+'\n')
 print('PQ_COUNT_PINS PASS masters15/2 outline142.56x19.44')

if __name__=='__main__':main()
