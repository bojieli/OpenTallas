#!/usr/bin/env python3
"""Draw actual component rectangles and representative pin-pair connections to scale."""
import argparse,html,json
from pathlib import Path
from hbm_geometry_pin_search import build

def draw(m,r):
 cs,pairs,_=build(m);W,H=m['outline_um'];scale=760/W;out=['<svg xmlns="http://www.w3.org/2000/svg" width="1660" height="490" viewBox="0 0 1660 490">','<rect width="1660" height="490" fill="#f7f9fc"/>','<g font-family="Arial,sans-serif" fill="#18283d">','<text x="35" y="32" font-size="23">HBM attention hi: actual pin geometry, before and candidate</text>','<text x="35" y="58" font-size="14">Same scale and outline in both panels. Lines connect representative actual pins; they are not routed wires.</text>']
 selected={ (g['net'],g['source'],g['sink']) for g in r['top20_before'] };groups={}
 for a,b,ap,bp,net,k in pairs:
  key=(net,a,b)
  if key in selected and key not in groups:groups[key]=(ap[0],bp[0])
 for panel,(title,deltas) in enumerate([('Before: repaired source layout',{}),('Candidate: 10 local translations',r['placement_deltas_um'])]):
  x0=35+panel*820;y0=115
  out.append(f'<text x="{x0}" y="95" font-size="19">{title}</text>')
  out.append(f'<rect x="{x0}" y="{y0}" width="{W*scale}" height="{H*scale}" fill="white" stroke="#18283d"/>')
  def point(x,y):return x0+x*scale,y0+(H-y)*scale
  for n,c in cs.items():
   dx,dy=deltas.get(n,[0,0]);x,y=c['xy_um'];w,h=c['outline_um'];px,py=point(x+dx,y+dy+h);fill='#f2a852' if n in r['placement_deltas_um'] else '#c6d5e6';out.append(f'<rect x="{px:.3f}" y="{py:.3f}" width="{w*scale:.3f}" height="{h*scale:.3f}" fill="{fill}" stroke="#4f6279" stroke-width="0.7"><title>{html.escape(n)}</title></rect>')
  for (net,a,b),(ap,bp) in groups.items():
   ad=deltas.get(a,[0,0]);bd=deltas.get(b,[0,0]);ax,ay=point(ap[0]+ad[0],ap[1]+ad[1]);bx,by=point(bp[0]+bd[0],bp[1]+bd[1]);out.append(f'<line x1="{ax:.3f}" y1="{ay:.3f}" x2="{bx:.3f}" y2="{by:.3f}" stroke="#275ea2" stroke-width="1.2" opacity="0.5"><title>{html.escape(net+": "+a+" to "+b)}</title></line>')
  stats=r['before' if panel==0 else 'after'];out.append(f'<text x="{x0}" y="{y0+H*scale+28:.2f}" font-size="15">Data-pin distance sum: {stats["total_bit_um"]:,.0f} bit-µm; worst {stats["max_pin_manhattan_um"]:.2f} µm</text>')
 out+=['<text x="35" y="470" font-size="14">Orange: the same 10 movable children in both panels. Data-pin distance −8.31%; route, clocks and timing remain unqualified.</text>','</g></svg>'];return '\n'.join(out)+'\n'
def main():
 p=argparse.ArgumentParser();p.add_argument('manifest');p.add_argument('result');p.add_argument('--out',required=True);a=p.parse_args();Path(a.out).write_text(draw(json.load(open(a.manifest)),json.load(open(a.result))))
if __name__=='__main__':main()
