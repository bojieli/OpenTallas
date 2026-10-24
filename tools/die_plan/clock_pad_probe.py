#!/usr/bin/env python3
"""Clock-only trial ECO: add non-inverting delay buffers to fast tap branches.

Consumes measured TT arrivals from one immutable H-tree probe. This never changes data
RTL or a die plan and does not constitute physical signoff or authorize design adoption.
"""
import argparse,json,re,shutil
from collections import Counter
from pathlib import Path

def main():
 ap=argparse.ArgumentParser();ap.add_argument('baseline',type=Path);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--buffer-ps',type=float,default=20);a=ap.parse_args()
 if a.out.exists():raise SystemExit('new output directory required; preserve previous verdicts')
 a.out.mkdir(parents=True)
 for n in ('clock.tcl','sta_clock.tcl','make_tracks.tcl','pg_obs.tcl','run_clock.sh','build.json'):
  shutil.copy2(a.baseline/n,a.out/n)
 d=json.loads((a.baseline/'clock_tree.json').read_text());arr={p:float(v) for p,v in (x.split() for x in (a.baseline/'clock_arr_TT.txt').read_text().splitlines())}
 target=max(arr[t['inst']+'/CLK'] for t in d['taps']);text=(a.baseline/'clock.def').read_text();dbu=int(re.search(r'UNITS DISTANCE MICRONS (\d+)',text)[1]);extra_comps=[];extra_nets=[];counts=Counter();W,H=json.loads((a.out/'build.json').read_text())['outline_um']
 for i,t in enumerate(d['taps']):
  tip=t['inst'];n=max(0,round((target-arr[tip+'/CLK'])/a.buffer_ps));counts[n]+=1;t['padding_buffers']=n
  if not n:continue
  prev=d['parent'][tip];first=f'ckpad_{i}_0'
  old=f'( {tip} CLK )';new=f'( {first} A )'
  if text.count(old)!=1:raise ValueError(f'{tip}: expected one sink')
  text=text.replace(old,new)
  for j in range(n):
   nm=f'ckpad_{i}_{j}';x=min(W-2,max(1,t['x']+(j%5)*1.4));y=min(H-2,max(1,t['y']+(j//5)*1.4))
   extra_comps.append(f'- {nm} BUFx16f_ASAP7_75t_R + PLACED ( {round(x*dbu)} {round(y*dbu)} ) N ;')
   d['parent'][nm]=prev;prev=nm
   sink=f'( ckpad_{i}_{j+1} A )' if j+1<n else f'( {tip} CLK )'
   extra_nets.append(f'- ck_{nm} ( {nm} Y ) {sink} + USE CLOCK ;')
  d['parent'][tip]=prev
 text=re.sub(r'COMPONENTS (\d+) ;',lambda m:f'COMPONENTS {int(m[1])+len(extra_comps)} ;',text,count=1)
 text=text.replace('END COMPONENTS','\n'.join(extra_comps)+'\nEND COMPONENTS')
 text=re.sub(r'\nNETS (\d+) ;',lambda m:f'\nNETS {int(m[1])+len(extra_nets)} ;',text,count=1)
 text=text.replace('END NETS','\n'.join(extra_nets)+'\nEND NETS')
 (a.out/'clock.def').write_text(text);d['cells']['BUFx16f_ASAP7_75t_R']+=len(extra_comps);d['padding']=dict(measured_corner='TT',target_ps=target,estimated_buffer_ps=a.buffer_ps,buffers=len(extra_comps),histogram=dict(counts),added_data_cycles=0)
 (a.out/'clock_tree.json').write_text(json.dumps(d));print(json.dumps(d['padding']))
if __name__=='__main__':main()
