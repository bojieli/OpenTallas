#!/usr/bin/env python3
"""Candidate face directions at actual recipe scale; not invented actual pin XY."""
import argparse,json
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('coverage',type=Path);p.add_argument('out',type=Path);a=p.parse_args();d=json.loads(a.coverage.read_text());recipes={r['family']:r['candidate_leaf_outline']for r in d['entries']if r['candidate_leaf_outline']is not None}
 for f,size in [('head',(172.8,129.6)),('exp',(129.6,151.2)),('rcp',(108,129.6)),('rsq',(129.6,151.2))]:
  if (recipes[f]['w'],recipes[f]['h'])!=size:raise ValueError('Source recipe outline changed; reassess candidate packing')
 out=['<svg xmlns="http://www.w3.org/2000/svg" width="1320" height="680" viewBox="0 0 1320 680"><defs><marker id="a" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10z" fill="#406f91"/></marker></defs><rect width="100%" height="100%" fill="white"/>','<text x="25" y="27" font-size="18">SU lane-facing options from actual recipe dimensions and source pin faces</text>','<text x="25" y="49" font-size="12">One source lane cohort at identical scale; eight belong to each octet. Face markers are illustrative directions, not actual pin coordinates.</text>']
 s=1.12
 for panel,flip in enumerate([False,True]):
  ox=35+panel*650;oy=110;H=324;out.append(f'<text x="{ox}" y="86" font-size="14">{"A: retain all current recipe orientations"if not flip else "B: reciprocal MX candidate to face head N"}</text>')
  def rect(n,x,y,w,h,c):
   X=ox+x*s;Y=oy+(H-y-h)*s;out.append(f'<rect x="{X:.2f}" y="{Y:.2f}" width="{w*s:.2f}" height="{h*s:.2f}" fill="{c}" stroke="#546271"/><text x="{X+4}" y="{Y+17}" font-size="11">{n}</text><text x="{X+4}" y="{Y+32}" font-size="9">{w} × {h} µm</text>')
  def face(x,y,label,c):
   X=ox+x*s;Y=oy+(H-y)*s;out.append(f'<circle cx="{X:.2f}" cy="{Y:.2f}" r="4" fill="{c}"/><text x="{X+6:.2f}" y="{Y-6:.2f}" font-size="10">{label}</text>');return X,Y
  rect('head',108,0,172.8,129.6,'#a6bdcf');rect('exp',0,151.2,129.6,151.2,'#d9b787');rect('rsqrt',151.2,151.2,129.6,151.2,'#d9b787');rect('reciprocal '+('MX?'if flip else 'R0'),302.4,151.2,108,129.6,'#e4c599');rect('relay*',0,0,71.28,71.28,'#d7d7d7')
  h=face(194.4,129.6,'SFU N','#675a9d');e=face(64.8,151.2,'S','#675a9d');r=face(216,151.2,'S','#675a9d');q=face(356.4,151.2 if flip else 280.8,'S?'if flip else 'N','#c78034')
  for X,Y in(e,r,q):out.append(f'<path d="M{h[0]},{h[1]} L{X},{Y}" stroke="#406f91" stroke-width="2" fill="none" marker-start="url(#a)" marker-end="url(#a)"/>')
  face(194.4,0,'VM/CROM S','#287e94');face(108,70,'control W','#c16f35');out.append(f'<text x="{ox}" y="495" font-size="11">Head N: exp/rcp/rsq request + return ports in source pin plan.</text><text x="{ox}" y="514" font-size="11">Head S: memory operands/addresses; put corresponding bank/align faces here.</text>')
 out+=['<rect x="25" y="540" width="1270" height="105" fill="#e0e0e0" stroke="#888"/>','<text x="40" y="562" font-size="12">Gates: source-equivalent physical views, legal orientation, actual pin XY/PG, clock transform/phi−R, activity and extracted route.</text>','<text x="40" y="583" font-size="11">Reciprocal recipe has N data pins; MX would face them south. No legal-orientation or native timing admission is inferred.</text>','<text x="40" y="604" font-size="11">* Relay 71.28 µm recipe is a component, not a proven input/output return placement. Octet may require separate source-preserving stage homes/roots.</text>','<text x="40" y="625" font-size="11">Alignment / VM / copy / residual base homes remain unassigned. No full-SU fit, global floorplan or added pipeline performance claim.</text>',f'<text x="25" y="667" font-size="10">Recipe source hashes in {a.coverage.name}; original source ABI {d["source_commit"]}. Separate 347-root copy successor requires current integration.</text></svg>'];a.out.write_text('\n'.join(out)+'\n')
if __name__=='__main__':main()
