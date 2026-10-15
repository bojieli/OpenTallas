#!/usr/bin/env python3
"""To-scale diagnostic figure from source-pinned system candidate rectangles."""
import argparse,json
from pathlib import Path

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--report',type=Path,required=True);ap.add_argument('--capacity',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 p=json.loads(a.report.read_text());cap=json.loads(a.capacity.read_text());scale=.015
 s=['<svg xmlns="http://www.w3.org/2000/svg" width="1670" height="650" viewBox="0 0 1670 650"><rect width="1670" height="650" fill="#f8fafc"/><g font-family="sans-serif" fill="#16243a"><text x="25" y="30" font-size="22">HISTORICAL — superseded 164-node VM geometry study</text><text x="25" y="54" font-size="14">Each die is drawn at the same scale: 33 × 26 mm. All 128 field regions / 2,417 pairs remain in their canonical homes.</text>']
 def rect(x,y,w,h,fill,stroke='#ffffff',sw=.6):s.append(f'<rect x="{x:.3f}" y="{y:.3f}" width="{w:.3f}" height="{h:.3f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
 labels=['A: expand VM vertically in place','B: compact 2 × 2 VM + move HC','C: VM grouped near two client regions']
 details=['48 rectangle collisions; no reticle overflow','0 rectangle collisions; HC shifts east 324 µm','0 rectangle collisions; distributed service cost open']
 for i,q in enumerate(p['options']):
  x0=25+550*i;y0=110
  s.append(f'<text x="{x0}" y="85" font-size="17">{labels[i]}</text>');rect(x0,y0,33000*scale,26000*scale,'#e2e8f0','#64748b',1)
  def drawbox(b,fill):
   x,y=b['xy_um'];w,h=b['outline_um'];rect(x0+x*scale,y0+(26000-y-h)*scale,w*scale,h*scale,fill)
  for f in cap['placements']:drawbox(dict(xy_um=f['origin_um'],outline_um=f['outline_um']),'#bfdbfe')
  for b in q['fixed']:
   name=b['name'];color='#a78bfa' if name.startswith('sp_hc') else '#fbbf24' if b['kind'].startswith('unbound_HCP') else '#94a3b8'
   drawbox(b,color)
  for n in q['vm_nodes']:drawbox(n,'#10b981' if i else '#ef4444')
  drawbox(q['edge'],'#fde68a')
  s.append(f'<text x="{x0}" y="525" font-size="13">{details[i]}</text>')
  s.append(f'<text x="{x0}" y="547" font-size="12">128 SRAM banks / 164 core nodes in this diagnostic template.</text>')
 s.extend(['<text x="25" y="585" font-size="14">Blue: canonical field regions. Green/red: VM core children. Purple: HC towers. Amber: HCP / global edge reservations.</text>',
 '<text x="25" y="611" font-size="13">Geometry study only. This 164-node VM template fails exact pin reach; the 188-node structural successor is pending.</text>',
 '<text x="25" y="634" font-size="13">No global pin-route, cut, clock, throughput or full VM edge-fit qualification is implied. Existing transport must be regenerated.</text></g></svg>'])
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(''.join(s))
if __name__=='__main__':main()
