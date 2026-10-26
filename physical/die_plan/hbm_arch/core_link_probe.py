#!/usr/bin/env python3
"""HBM core-link congestion diagnostic, complementing G2's boundary/FT-only probe.

Each declared core_conns port->core leg uses its real source pin centroid and
nearest target face; planned internal stations are inserted in order. Every bit
is routed. This is conservative directed-leg demand, not RTL binding or signoff.
"""
import argparse,collections,json,os,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'tools/die_plan'),str(Path(__file__).parent)]
import schema as S,g2,cores_b2 as B

def main():
 a=argparse.ArgumentParser();a.add_argument('plan',type=Path);a.add_argument('--type',default='q_hub');a.add_argument('--out',type=Path,required=True);z=a.parse_args()
 raw=json.loads(z.plan.read_text());P=S.Plan(raw);t=P.types[z.type];out=g2.part_probe(P,z.type,z.out,adjust=.5,mem=64)
 conns=json.loads(z.plan.with_name('core_conns.json').read_text())[z.type];cores={c['inst']:c for c in t['hard_cores']};w,h=t['outline_um'];boxes=[(*c['origin_um'],*c['outline_um']) for c in cores.values()]
 stations={e['conn']:e for e in t.get('internal_stations',[])};cells=[];nets=[];places=[];legs=[]
 for name,c in cores.items():
  pins=json.loads((z.plan.parent/c['pins_file']).read_text());pins=pins.get('pins',pins) if isinstance(pins,dict) else pins
  by=collections.defaultdict(list)
  for pin in pins:
   if isinstance(pin,dict): nm=pin['name'];x,y=pin['x'],pin['y']
   else:nm,_,x,y=pin
   by[re.sub(r'\[.*','',nm)].append((c['origin_um'][0]+x,c['origin_um'][1]+y))
  for port,targets in conns.get(name,{}).items():
   if port not in by:continue
   pp=by[port];A=(sum(p[0] for p in pp)/len(pp),sum(p[1] for p in pp)/len(pp))
   for target in targets:
    if not target.startswith('core:'):continue
    q=target[5:]
    if q not in cores:continue
    d=cores[q];x,y=d['origin_um'];cw,ch=d['outline_um'];end=(min(max(A[0],x),x+cw),min(max(A[1],y),y+ch));key=f'{name}.{port}|{q}'
    e=stations.get(key);sites=[B.free_point(A,boxes,w,h)]+([tuple(p) for p in e['regs_um']] if e else [])+[B.free_point(end,boxes,w,h)]
    k=len(legs);legs.append(dict(conn=key,bits=len(pp),sites=sites))
    for bit in range(len(pp)):
     for j,site in enumerate(sites):
      cell=f'cl_{k}_{bit}_{j}';net=f'n_{cell}';prev=f'n_cl_{k}_{bit}_{j-1}' if j else f'd_{cell}'
      if not j:nets.append(prev)
      nets.append(net);cells.append(f'  {g2.FLOP} {cell} (.D({prev}), .QN({net}));');places.append((cell,*site))
 v=(out/'probe.v').read_text();v=v.replace('endmodule','\n'.join(f'  wire {n};' for n in nets)+'\n'+'\n'.join(cells)+'\nendmodule');(out/'probe.v').write_text(v)
 tc=(out/'probe.tcl').read_text();p='\n'.join(f'place_inst -name {n} -location {{{min(max(x,1),w-2):.3f} {min(max(y,1),h-1.3):.3f}}} -status PLACED' for n,x,y in places);tc=tc.replace('detailed_placement -max_displacement',p+'\ndetailed_placement -max_displacement');(out/'probe.tcl').write_text(tc)
 # Coordinate image is reviewed before execution; all endpoint sites are macro-free.
 import matplotlib.pyplot as plt
 from matplotlib.patches import Rectangle
 f,ax=plt.subplots(figsize=(12,8))
 for x,y,cw,ch in boxes:ax.add_patch(Rectangle((x,y),cw,ch,color='gray',alpha=.4))
 for e in legs:
  xs,ys=zip(*e['sites']);ax.plot(xs,ys,lw=.3,alpha=.25);ax.scatter(xs,ys,s=.5)
 ax.set(xlim=(0,w),ylim=(0,h),aspect='equal',title=f'{z.type}: {len(legs)} directed core legs / {sum(e["bits"] for e in legs)} bits');f.savefig(out/'core_links.png',dpi=130)
 (out/'core_links.json').write_text(json.dumps(dict(scope=__doc__,legs=legs,flops=len(places),bits=sum(e['bits'] for e in legs)),indent=1)+'\n');print(out,'legs',len(legs),'bits',sum(e['bits'] for e in legs),'flops',len(places))
if __name__=='__main__':main()
