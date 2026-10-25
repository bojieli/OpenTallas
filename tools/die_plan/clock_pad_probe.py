#!/usr/bin/env python3
"""Clock-only trial ECO: add non-inverting delay buffers to fast tap branches.

Consumes measured TT arrivals from one immutable H-tree probe. This never changes data
RTL or a die plan and does not constitute physical signoff or authorize design adoption.

Default: every tap gets round((max - its arrival) / buffer_ps) buffers in front of its clock pin.
--at-branches (TRIAL-QK 2026-10-24, owner decision 5(d)/(f)): balance at the tree's branch points instead -- the
child branch with the earlier subtree-latest arrival gets the difference as a delay chain at its head, so padding
sits where it is common to every sink below (CPPR cancels it for related pairs) and the buffer count falls with the
number of branches, not taps.  Per sink the total equals the tap-level padding (telescoping, same rounding).
"""
import argparse,json,re,shutil
from collections import Counter, defaultdict
from pathlib import Path


def branch_pads(d, arr, target, buffer_ps):
    """{(parent, child): n buffers}: cumulative pad wanted at child c = round((target - latest(c)) / buffer_ps), where
    latest(c) = latest measured tap arrival below c; edge pad = cum(c) - cum(parent) (>= 0, telescopes to the tap pad)."""
    par = d['parent']
    kids = defaultdict(list)
    for c, p in par.items():
        if p is not None:
            kids[p].append(c)
    latest = {}
    for t in d['taps']:
        i = t['inst']
        v = arr[i + '/CLK']
        while i is not None and latest.get(i, -1e18) < v:
            latest[i] = v
            i = par.get(i)
    cum = {i: max(0, round((target - v) / buffer_ps)) for i, v in latest.items()}
    pads = {}
    for c, p in par.items():
        if p is None or c not in cum:
            continue
        n = cum[c] - cum.get(p, 0)
        if n > 0:
            pads[(p, c)] = n
    return pads


def main():
 ap=argparse.ArgumentParser();ap.add_argument('baseline',type=Path);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--buffer-ps',type=float,default=20)
 ap.add_argument('--at-branches',action='store_true',help='balance at branch points (pads common to the subtree)')
 ap.add_argument('--corner',default='TT',help='corner whose measured arrivals are balanced (FF: hold is the tight die check; buffer step scaled by the FF/TT insertion ratio)');a=ap.parse_args()
 if a.out.exists():raise SystemExit('new output directory required; preserve previous verdicts')
 a.out.mkdir(parents=True)
 for n in ('clock.tcl','sta_clock.tcl','make_tracks.tcl','pg_obs.tcl','run_clock.sh','build.json'):
  shutil.copy2(a.baseline/n,a.out/n)
 d=json.loads((a.baseline/'clock_tree.json').read_text())
 rd=lambda c:{p:float(v) for p,v in (x.split() for x in (a.baseline/f'clock_arr_{c}.txt').read_text().splitlines()) if v not in ('NA','')}
 arr=rd(a.corner)
 if a.corner!='TT':
  tt=rd('TT');k=[t['inst']+'/CLK' for t in d['taps']]
  a.buffer_ps=round(a.buffer_ps*sum(arr[x] for x in k)/sum(tt[x] for x in k),2)
 target=max(arr[t['inst']+'/CLK'] for t in d['taps']);text=(a.baseline/'clock.def').read_text();dbu=int(re.search(r'UNITS DISTANCE MICRONS (\d+)',text)[1]);extra_comps=[];extra_nets=[];counts=Counter();W,H=json.loads((a.out/'build.json').read_text())['outline_um']
 if a.at_branches:
  pos={m[1]:(int(m[2])/dbu,int(m[3])/dbu) for m in re.finditer(r'^- (\S+) \S+ \+ PLACED \( (-?\d+) (-?\d+) \)',text,re.M)}
  taps={t['inst'] for t in d['taps']}
  pads=branch_pads(d,arr,target,a.buffer_ps)
  for i,((p,c),n) in enumerate(sorted(pads.items())):
   counts[n]+=1
   pin='CLK' if c in taps else 'A'
   old=f'( {c} {pin} )';first=f'ckpadb_{i}_0'
   if text.count(old)!=1:raise ValueError(f'{c}: expected one sink')
   text=text.replace(old,f'( {first} A )')
   cx,cy=pos[c];prev=p
   for j in range(n):
    nm=f'ckpadb_{i}_{j}';x=min(W-2,max(1,cx+(j%5)*1.4));y=min(H-2,max(1,cy+(j//5)*1.4))
    extra_comps.append(f'- {nm} BUFx16f_ASAP7_75t_R + PLACED ( {round(x*dbu)} {round(y*dbu)} ) N ;')
    d['parent'][nm]=prev;prev=nm
    sink=f'( ckpadb_{i}_{j+1} A )' if j+1<n else f'( {c} {pin} )'
    extra_nets.append(f'- ck_{nm} ( {nm} Y ) {sink} + USE CLOCK ;')
   d['parent'][c]=prev
  for t in d['taps']:
   t['padding_buffers']=max(0,round((target-arr[t['inst']+'/CLK'])/a.buffer_ps))
 else:
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
 (a.out/'clock.def').write_text(text);d['cells']['BUFx16f_ASAP7_75t_R']+=len(extra_comps);d['padding']=dict(measured_corner=a.corner,target_ps=target,estimated_buffer_ps=a.buffer_ps,buffers=len(extra_comps),histogram=dict(counts),added_data_cycles=0,mode='branches' if a.at_branches else 'taps')
 (a.out/'clock_tree.json').write_text(json.dumps(d));print(json.dumps(d['padding']))
if __name__=='__main__':main()
