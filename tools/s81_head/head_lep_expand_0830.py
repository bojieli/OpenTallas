#!/usr/bin/env python3
"""HEAD measured-channel fix: reserve 777.6x492.48 pairs plus native SRAMs.

Candidate only until child pins, CA recomposition and full geometry gates land.
The E and N external pin positions stay at their die coordinates; nst4 is
cropped at its E edge to donate channel whitespace. No signal cycle is added.
"""
import copy,json,sys,math
from pathlib import Path

def build(p):
 p=copy.deepcopy(p);ts=p['partition_types'];t=ts['hd_lep0N'];grow=302.4
 assert t['outline_um']==[1442.88,1226.88]
 t['outline_um'][0]=1745.28
 for b in t['buses']:
  if b['face'] in ('N','S'):b['window_um']=[round(v+grow,6) for v in b['window_um']]
 for q in t.get('contents',[]):
  if 'origin_um' in q:q['origin_um'][0]+=grow
 c=t['clock'];c['tap_um'][0]+=grow
 for xy in t.get('reset',{}).get('local_taps_um',[]):xy[0]+=grow
 for r in c.get('die_islands_um',[]):r[0]+=grow;r[2]+=grow
 for s in t.get('internal_stations',[]):
  for k in ('from_um','to_um','leaf_um'):
   if k in s:s[k][0]+=grow
  for xy in s['regs_um']:xy[0]+=grow
 pairs=[x for x in t['hard_cores'] if x['module']=='ot_s81hd_lep_pair']
 assert len(pairs)==4
 # Keep pair0 near N coll0; pair1/2 near the W pair links; pair3 near E.
 homes={0:(864.,665.28),1:(69.12,665.28),2:(69.12,155.52),3:(864.,155.52)}
 for h in pairs:
  i=int(h['inst'].split('g_pp[')[1].split(']')[0]);h['origin_um']=list(homes[i]);h['outline_um']=[777.6,492.48]
  h['pins_file']='child/lep_pair_pins.json'
  h['note']='HEAD channel closure candidate: enlarged native pair; actual matching child pins/views required'
 sr=[x for x in t['hard_cores'] if x not in pairs]
 groups={}
 for x in sr:groups.setdefault(tuple(x['outline_um']),[]).append(x)
 big=groups[(169.368,29.16)];small=groups[(51.432,20.808)];medium=groups[(91.8,39.432)]
 assert (len(big),len(small),len(medium))==(20,20,5)
 for i,h in enumerate(big):h['origin_um']=[round(8.64+(i%9)*177.12,3),round(8.64+(i//9)*37.8,3)]
 for i,h in enumerate(medium):h['origin_um']=[round(380.16+i*103.68,3),84.24]
 for i,h in enumerate(small):h['origin_um']=[round(907.2+(i%13)*60.48,3),round(84.24+(i//13)*30.24,3)]
 for h in sr:
  h['origin_um']=[round(math.ceil(v/8.64-1e-8)*8.64,3) for v in h['origin_um']]
  h['orient']='R0';h['note']='HEAD channel closure: native parent SRAM bottom shelf; exact dimensions retained'
 c['tap_um']=[855.36,656.64]
 c['die_islands_um']=[[851.04,652.32,859.68,660.96]]
 def free(xy):
  return not any(h['origin_um'][0]-4.32<xy[0]<h['origin_um'][0]+h['outline_um'][0]+4.32 and h['origin_um'][1]-4.32<xy[1]<h['origin_um'][1]+h['outline_um'][1]+4.32 for h in t['hard_cores'])
 t['reset']['local_taps_um']=[xy for xy in t['reset']['local_taps_um'] if free(xy)]
 # consumer_taps adds clock.tap_um itself; do not declare that site twice.
 t['reset']['local_taps_um']+=[[855.36,y] for y in (155.52,397.44,907.2,1157.76)]
 t['reset']['local_taps_um']=[list(x) for x in dict.fromkeys(tuple(x) for x in t['reset']['local_taps_um'])]
 for q in p['partitions']:
  if q['type']=='hd_lep0N':assert q.get('orient','R0')=='R0';q['origin_um'][0]=round(q['origin_um'][0]-grow,3)
 assert ts['hd_st_n4']['outline_um'][0]==1442.88
 n=ts['hd_st_n4'];n['outline_um'][0]=1140.48
 n['clock']['tap_um'][0]=570.24
 n['clock']['die_islands_um']=[r for r in n['clock'].get('die_islands_um',[]) if r[2]<=1140.48]
 n['reset']['local_taps_um']=[xy for xy in n['reset']['local_taps_um'] if xy[0]<=1136.16]
 for k,xy in p.get('reset',{}).get('in_sites',{}).items():
  if k=='hd_lep0N':xy[0]+=grow
 p['note']+=' | HEAD LEP channel candidate: lep0N west +302.4, nst4 E crop;4 native pair outlines777.6x492.48,45 parent SRAMs bottom shelf; no added cycles'
 return p

if __name__=='__main__':
 p=build(json.load(open(sys.argv[1])));Path(sys.argv[2]).write_text(json.dumps(p,indent=1)+'\n')
