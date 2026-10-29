#!/usr/bin/env python3
"""Read-only synthesized SRAM face net census; tie pins are counted separately."""
import re,json,sys
from pathlib import Path
from collections import Counter
R=Path(sys.argv[1]);lef=(R/'sram.lef').read_text();pins={}
for m in re.finditer(r'^  PIN (\S+)\n(.*?)^  END \1$',lef,re.M|re.S):
 n,b=m.groups();a=re.search(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',b)
 if a:
  x1,y1,x2,y2=map(float,a.groups());pins[n]='W' if (x1+x2)/2<47 else 'E'
report={}
for q in [1,2]:
 s=(R/f'q{q}.v').read_text();ties=set()
 for b in re.findall(r'\bTIE(?:LO|HI)\w*\s+[^;]+;',s,re.S):
  ties.update(re.findall(r'\.(?:L|H)\(\s*([^()\s]+)\s*\)',b))
 blocks=re.findall(r'ot_sram_1r1w_128x256_m1_r2c2\s+(\\\S+|\w+)\s*\((.*?)\);',s,re.S)
 rows=[]
 for name,b in sorted(blocks):
  con={}
  for pn,v in re.findall(r'\.(\w+)\(([^()]*)\)',b,re.S):
   bits=[a.strip() for a in v.strip().strip('{}').split(',')]
   for i,net in enumerate(reversed(bits)): con[f'{pn}[{i}]' if len(bits)>1 else pn]=net
  faces={side:dict(pins=0,tied_pins=0,active_pins=0,active_nets=set(),tie_nets=set()) for side in ['W','E']}
  for pn,side in pins.items():
   net=con.get(pn)
   if net is None:continue
   f=faces[side];f['pins']+=1
   if net in ties or re.match(r"\d+'[bhd][01xz]+$",net):f['tied_pins']+=1;f['tie_nets'].add(net)
   else:f['active_pins']+=1;f['active_nets'].add(net)
  rows.append(dict(instance=name,faces=faces))
 # Static macro_sites ordering puts instances0/1 left,2/3 right; rowsbottom0/2 andtop1/3.
 pairs=[]
 for a,b in [(0,2),(1,3)]:
  fs=[rows[a]['faces']['E'],rows[b]['faces']['W']]
  nets=set().union(*(x['active_nets'] for x in fs));tn=set().union(*(x['tie_nets'] for x in fs))
  pairs.append(dict(instances=[rows[a]['instance'],rows[b]['instance']],physical_pins=sum(x['pins'] for x in fs),active_pins=sum(x['active_pins'] for x in fs),unique_active_nets=len(nets),unique_tie_nets=len(tn),raw_channel_um=12.744,raw_M3_M5_tracks=12.744*(1/.036+1/.048),ratio=len(nets)/(12.744*(1/.036+1/.048))))
 for r in rows:
  for f in r['faces'].values():f['active_nets']=len(f['active_nets']);f['tie_nets']=len(f['tie_nets'])
 report[f'q{q}']=dict(tie_nets=sorted(ties),macros=rows,middle_pairs=pairs,assumptions='M3/M5 raw vertical supply; halo restricts cells, not routing. No congestion/PG/other nets deducted; placement GRT still required.')
print(json.dumps(report,indent=2))
