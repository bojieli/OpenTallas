#!/usr/bin/env python3
"""Select one legal diagnostic PG contact per macro term from direct candidates.
This tests physical accessibility only, never current capacity or full PG closure.
The ONLY host OBS exception is M7 via metal wholly inside actual same-net pin.
"""
import argparse,collections,json
from pathlib import Path
from shapely.geometry import box
from shapely.strtree import STRtree

def hit(a,b):return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]
def inside(a,b):return b[0]<=a[0] and b[1]<=a[1] and a[2]<=b[2] and a[3]<=b[3]
def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--geometry',required=True);p.add_argument('--grid',required=True);p.add_argument('--reserved',action='append',default=[]);p.add_argument('--out',required=True);a=p.parse_args()
 x=json.load(open(a.plan));g=json.load(open(a.geometry));D=x['dbu'];assert D==g['dbu'];grid=json.load(open(a.grid));gridkeys={(ly,*[round(v*D) for v in r]) for n,ly,*r in grid};obs=collections.defaultdict(list);sig=collections.defaultdict(list)
 for owner,ly,*r in g['obstructions']:
  if ly not in ['M7','M8']:continue
  if owner=='BLOCK' and (ly,*r) in gridkeys:continue
  obs[ly].append((owner,r))
 for inst,pin,ly,*r in g['signal_shapes']:
  if ly in ['M7','M8']:sig[ly].append((inst+'/'+pin,r))
 for n,ly,*r in g['existing_supplies']:
  if ly in ['M7','M8']:sig[ly].append((n,r))
 for f in a.reserved:
  for n,ly,*r in json.load(open(f)):
   if ly in ['M7','M8']:sig[ly].append((n,[round(v*D) for v in r]))
 trees={k:{ly:STRtree([box(*r) for _,r in rr]) for ly,rr in data.items()} for k,data in [('obs',obs),('sig',sig)]};print('indexed', {k:len(v) for k,v in obs.items()},{k:len(v) for k,v in sig.items()},flush=True)
 grouped=collections.defaultdict(list)
 for q in x['contacts']:grouped[q['inst'],q['pin']].append(q)
 chosen=[];failed=[];rejections=collections.Counter()
 for key,cc in grouped.items():
  # One term-access coupon; prefer long native straps, no new metal beyond native supplies.
  cc.sort(key=lambda q:-(q['native_pin_dbu'][2]-q['native_pin_dbu'][0])*(q['native_pin_dbu'][3]-q['native_pin_dbu'][1]))
  ok=None;last=None
  for c in cc:
   legal=True
   for ly,r in c['metal_dbu'].items():
    sp={'M7':32,'M8':40}[ly];e=[r[0]-sp,r[1]-sp,r[2]+sp,r[3]+sp];qb=box(*e)
    for kind,data in [('obs',obs),('sig',sig)]:
     tree=trees[kind].get(ly)
     if tree is None:continue
     for idx in tree.query(qb):
      owner,rr=data[ly][idx]
      if not hit(e,rr):continue
      if kind=='obs' and ly=='M7' and owner==c['inst'] and inside(r,c['native_pin_dbu']):continue
      if kind=='sig' and owner==c['net']:continue
      legal=False;last=[ly,kind,owner,rr];rejections[ly+'_'+kind]+=1;break
     if not legal:break
    if not legal:break
   if legal:ok=c;break
  if ok:chosen.append(ok)
  else:failed.append(dict(inst=key[0],pin=key[1],candidates=len(cc),last_obstacle=last))
 out=Path(a.out);out.mkdir(parents=True,exist_ok=True);json.dump(dict(source=x['source'],dbu=D,contacts=chosen,failed=failed,scope='one contact per term connectivity coupon; no IR or per-fragment closure'),open(out/'selected_plan.json','w'),separators=(',',':'))
 result=dict(terms=len(grouped),selected=len(chosen),failed=len(failed),rejections=dict(rejections),direct_native_fragments=len(x['contacts']),unreached_native_fragments=len(x['failed']),verdict='READY_FOR_VISUAL_REVIEW' if not failed else 'HOLD_INCOMPLETE')
 (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
