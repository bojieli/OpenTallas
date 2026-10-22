#!/usr/bin/env python3
"""Land short standard-width region crossings with existing real landing views.
No extra relay hop: source clock gate writes D4 ring; K2 read gives age3.
Only opt-in per-link force_landing changes the legacy zero-station behavior.
Existing modeled lane ages stay equal within each receiving bundle.
Usage: land_short_g9e.py PLAN TABLE LAND_IN LAND_OUT
"""
import json, math, re, sys
from pathlib import Path

def main():
 pp,tp,lp,out=sys.argv[1:5]
 p=json.load(open(pp));t=json.load(open(tp));d=json.load(open(lp));rows={r['link']:r for r in d['links']}
 added=[];changed=[];B=p['blocks']
 for l in p['links']:
  dst=B[l['e'][1][0]];rule=t['masters'][dst['master']].get('ports',{}).get(l['e'][1][1]+'.i',{})
  if not rule.get('land') or (l['b'] not in (70,276,512,562,682) and not rule.get('adapter')):continue
  n=l['i'].replace('-','_');N=l.get('s',0)
  if n in rows and N:continue
  E=max(2,math.ceil(.47*N)+1)
  if E>7 and l['b']!=276:raise ValueError(f'{n}: no existing long view for {l["b"]}b E{E}')
  r=dict(link=n,cls=l['c'],dst=dst['name'],bits=l['b'],stages=N,E=E,K=E,D=8 if E>7 else 4,
   master=rule.get('adapter') or (f'dsfd_dvland_{l["b"]}'+('l' if E>7 else '')),force_landing=not N,model=True,
   K_source='G9e short crossing: real source-gated ring, fixed E2 K2 age3 at N0; nonzero ceil(.47N)+1')
  rows[n]=r;added.append(n)
 groups={}
 for n,r in rows.items():
  m=re.fullmatch(r'(.+)_l(\d+)',n)
  if m:groups.setdefault((m[1],r['dst']),[]).append(r)
 for key,g in groups.items():
  if not any(r['link'] in added for r in g):continue
  age=max(math.ceil(r.get('stages',0)/2)+r['K']+1 for r in g)
  for r in g:
   K=age-math.ceil(r.get('stages',0)/2)-1
   if K>7 and r['bits']!=276:raise ValueError(f'{key}: missing long view for bundle K{K}')
   if K>63:raise ValueError(f'{key}: K{K} exceeds existing long view')
   r.update(K=K,D=8 if K>7 else 4,master=f'dsfd_dvland_{r["bits"]}'+('l' if K>7 else ''))
   changed.append(r['link'])
 d['links']=list(rows.values());d['g9e_short_crossings']=dict(added=added,equal_age_links=changed,
  short_zero_age_cycles=3,ring_slots=4,closed_widths=[70,276,512,562,682],no_zero_station_exemption=True)
 Path(out).write_text(json.dumps(d,indent=1)+'\n');print(json.dumps(d['g9e_short_crossings']))
if __name__=='__main__':main()
