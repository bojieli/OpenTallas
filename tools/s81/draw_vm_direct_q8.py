#!/usr/bin/env python3
"""To-scale q8 natural dataflow; planned pins/geometry, not routed closure."""
import argparse,json,html
from pathlib import Path
from collections import defaultdict
p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=json.loads(a.report.read_text());sc=.52;x0=60;y0=88;H=1166.4
s=['<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="820" viewBox="0 0 1120 820"><rect width="1120" height="820" fill="#f8fafc"/><g font-family="sans-serif" fill="#17243b"><text x="30" y="31" font-size="22">S81 direct bank-local write microcluster</text><text x="30" y="55" font-size="14">True scale: 972 × 1166.4 µm. Actual-source planned pins; existing two scatter stages retained.</text>']
def xy(x,y):return x0+x*sc,y0+(H-y)*sc
def box(x,y,w,h,name,color):
 X,Y=xy(x,y+h);s.append(f'<rect x="{X}" y="{Y}" width="{w*sc}" height="{h*sc}" rx="2" fill="{color}" stroke="#64748b" stroke-width=".7"/><text x="{X+3}" y="{Y+min(14,h*sc/2+4)}" font-size="9">{html.escape(name)}</text>')
box(0,0,972,H,'','#eef2ff')
for b,(x,y) in enumerate([(43.2,43.2),(43.2,172.8),(518.4,43.2),(518.4,172.8),(43.2,432),(43.2,561.6),(518.4,432),(518.4,561.6)]):box(x,y,220.32,75.6,f'SRAM bank {b}','#bfdbfe')
for j,y in enumerate([86.4,475.2]):box(345.6,y,129.6,129.6,f'q4 {j}','#c4b5fd')
box(302.4,259.2,172.8,172.8,'Own b8 bridge','#a78bfa');box(302.4,648,172.8,86.4,'Output stage (R1)','#86efac')
box(108,820.8,734.4,345.6,'Dispatch: same 8 bank owners','#fde68a')
for b in range(8):box(864 if b<4 else 0,820.8+86.4*(b%4),86.4,86.4,f'Store {b}','#fcd34d')
for c in r['captures']:box(*c['xy_um'],43.2,43.2,f'C{c["bank"]}','#34d399')
colors={'dispatch_to_storage':'#b45309','storage_to_capture':'#059669','capture_to_output':'#0284c7','output_to_bridge':'#7c3aed'}
g=defaultdict(list)
for e in r['edges']:g[(e['kind'],e['bank'])].append(e)
for (kind,b),ee in g.items():
 sx=sum(e['source_um'][0] for e in ee)/len(ee);sy=sum(e['source_um'][1] for e in ee)/len(ee);tx=sum(e['target_um'][0] for e in ee)/len(ee);ty=sum(e['target_um'][1] for e in ee)/len(ee);X,Y=xy(sx,sy);XX,YY=xy(tx,ty)
 s.append(f'<path d="M{X},{Y} L{XX},{YY}" stroke="{colors[kind]}" stroke-width="1.4" opacity=".6" fill="none"/>')
s.append('<text x="605" y="113" font-size="18">Per-bit distance screen</text>')
y=143
for k,v in r['stats'].items():
 s.append(f'<rect x="605" y="{y-9}" width="12" height="12" fill="{colors[k]}"/><text x="628" y="{y}" font-size="13">{k.replace("_"," ")}</text><text x="628" y="{y+20}" font-size="13">{v["bits"]:,} endpoints; worst {v["max_manhattan_um"]:.3f} µm; over 500: {v["over500"]}</text>');y+=64
for line in ['7,464 writer endpoint bits per microcluster.','16 microclusters per VM512 (four per slice).','Source bank ownership eliminates pooled scatter traffic.','SOUTH drain pins remove storage-output U-turns.','Local banks, q4 and b8 keep source layout vectors.']:
 s.append(f'<text x="605" y="{y}" font-size="13">{html.escape(line)}</text>');y+=23
s.append('<text x="605" y="600" font-size="16">Still open at the system boundary</text>')
for i,line in enumerate(['W0 payload/header/control distribution and ages','Read issue, return repair and global fault trees','Additional VM cap16 / CDC16 / x34 hardware','Native pin IO, clock / phi-R, PG and route closure','Full traffic cuts and all 81-stage activity binding']):s.append(f'<text x="605" y="{627+i*23}" font-size="13">{html.escape(line)}</text>')
s.append('<text x="30" y="756" font-size="13">Bundle lines show direction by source → target; they are connectivity overlays, not detailed route guides.</text><text x="30" y="780" font-size="13">This local proof does not qualify complete VM packing or the die. Historical 164 / 188 / 200-node system figures are superseded.</text></g></svg>');a.out.write_text(''.join(s))
