#!/usr/bin/env python3
import argparse,json,gzip,html
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);p.add_argument('--out-dir',type=Path,required=True);a=p.parse_args();r=json.loads(a.report.read_text());plan=json.loads(gzip.decompress(a.plan.read_bytes()));a.out_dir.mkdir(parents=True,exist_ok=True)
sc=.017;s=['<svg xmlns="http://www.w3.org/2000/svg" width="1360" height="870" viewBox="0 0 1360 870"><rect width="1360" height="870" fill="#f8fafc"/><g font-family="sans-serif" fill="#17243b"><text x="25" y="32" font-size="22">Current S81 B / C — bank-local system grouping</text><text x="25" y="57" font-size="14">Actual 328 core + 150 write-edge leaves; 526 known clock roots, before cap / CDC and added distribution.</text>']
colors={'bank_local_memory':'#60a5fa','write_capture':'#10b981','write_output':'#059669','write_dispatch':'#f59e0b','write_storage':'#fbbf24','write_payload':'#f97316','write_header':'#fb923c','write_control':'#fb923c'}
for i,o in enumerate(r['options']):
 X=25+i*670;Y=115
 def draw(b,col):
  x,y=b['xy_um'];w,h=b['outline_um'];s.append(f'<rect x="{X+x*sc}" y="{Y+(26000-y-h)*sc}" width="{w*sc}" height="{h*sc}" fill="{col}" stroke="#fff" stroke-width=".25"/>')
 s.append(f'<text x="{X}" y="91" font-size="18">{html.escape(o["name"].replace("_"," "))}</text>');draw(dict(xy_um=[0,0],outline_um=[33000,26000]),'#e2e8f0')
 for f in r['field_regions']:draw(dict(xy_um=f['origin_um'],outline_um=f['outline_um']),'#bfdbfe')
 for f in o['fixed']:draw(f,'#fde68a' if f['kind']=='unbound_HCP' else '#a78bfa' if f['name'].startswith('sp_hc') else '#94a3b8')
 for n in o['nodes']:draw(n,colors[n['kind']])
 for x,y in o['slice_origins_um']:
  W,H=o['slice_known_outline_um'];s.append(f'<rect x="{X+x*sc}" y="{Y+(26000-y-H)*sc}" width="{W*sc}" height="{H*sc}" fill="none" stroke="#047857" stroke-width=".8"/>')
 lines=['470 actual leaf rectangles placed; 8 known read/control leaves UNPLACED.',f'Coarse actual field / hard / HCP collisions: {len(o["collisions"])}; outside: {len(o["outside"])}.',f'HC translation +{o["changes"]["hc_dx_um"]} µm; SU {o["changes"]["su_dx_um"]} µm.','Four real q8 writer groups per slice; zero added local write stages.','W0 → dispatch fanout needs staged global distribution / priced ages.','Cap16 / CDC16 / x34 and read-repair geometry remain additional.']
 for j,line in enumerate(lines):s.append(f'<text x="{X}" y="{588+23*j}" font-size="13">{html.escape(line)}</text>')
s.extend(['<text x="25" y="749" font-size="14">Known source boundaries: SU read request 240 bits → VM; VM → SU read return 8208 bits; SU write request 8688 bits → VM.</text>','<text x="25" y="774" font-size="14">Activity / serialization / physical all-81 stage binding remains missing; geometry alone cannot rank throughput or full routing cuts.</text>','<text x="25" y="802" font-size="14">B is the development direction. Both options are incomplete source-bound packing alternatives, not full VM/die fit or native qualification.</text>','<text x="25" y="830" font-size="14">Grey: SU/service clusters. Purple: HC. Blue: field/banks. Green: local write stages. Amber: actual dispatch/storage. Orange: W0 leaves.</text></g></svg>']);(a.out_dir/'current_B_C.svg').write_text(''.join(s))
# Exact SW corridor detail from actual constructed screen12 station boxes.
S=.7;gx=12232.944;gy=3100;H=750;s=['<svg xmlns="http://www.w3.org/2000/svg" width="1020" height="740" viewBox="0 0 1020 740"><rect width="1020" height="740" fill="#f8fafc"/><g font-family="sans-serif" fill="#17243b"><text x="25" y="32" font-size="22">Actual SW service spine — true aspect ratio</text><text x="25" y="58" font-size="14">Broad candidate shifts whole inner W column 146.88 µm; all root / pair identities retained.</text>']
def rect(x,y,w,h,col):s.append(f'<rect x="{100+(x-gx)*S}" y="{100+(gy+H-y-h)*S}" width="{w*S}" height="{h*S}" fill="{col}" stroke="#64748b" stroke-width=".5"/>')
rect(gx-40,gy,40,H,'#bfdbfe');rect(gx,gy,155.52,H,'#ecfdf5');rect(gx+155.52,gy,40,H,'#bfdbfe')
for c in plan['chain_paths']:
 if c['chain'] not in ['qSW','aSW','ixSW','coSW']:continue
 for st in c['stations']:
  x,y,X,Y=st['box']
  if gx<=st['center'][0]<=gx+155.52 and gy<=y<=gy+H:
   rect(x,y,X-x,Y-y,'#f59e0b' if c['chain']=='qSW' else '#10b981' if c['chain']=='aSW' else '#c4b5fd');s.append(f'<text x="260" y="{100+(gy+H-st["center"][1])*S+4}" font-size="12">{html.escape(c["chain"]+": "+st["orientation"]+" "+str(c["lanes"]))}</text>')
for i,line in enumerate(['155.52 µm actual column-to-column opening.','a1026 N/S station: 54.84 × 17.256 µm (R0).','q514 N/S station: 30.216 × 17.256 µm (MX).','Actual placed station boxes from partial screen 12.','','Declared q / a / ix / co: 2568 bits.','Declared lane cut: 0.524 before other traffic.','Clock / PG / control / halos still need actual proof.','','All four service flows now construct; generator','next fails at a separate control/service boundary.','No native route / congestion / timing pass claimed.']):s.append(f'<text x="475" y="{130+i*29}" font-size="14">{html.escape(line)}</text>')
s.append('<text x="25" y="690" font-size="14">Corridor height shown: 750 µm. Rectangles keep actual width / height proportions; space between stations is real.</text></g></svg>');(a.out_dir/'service_gap_actual.svg').write_text(''.join(s))
