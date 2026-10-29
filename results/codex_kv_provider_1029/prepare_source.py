#!/usr/bin/env python3
"""Add exact declared native START/reset endpoints to the e27f route source.
The clock-only/FT combo omitted these interfaces. Preserve all source objects,
append only existing plan-declared landing pins and their own scalar nets.
No test driver or die-input is substituted for a native partition output.
"""
import argparse,collections,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--kit',required=True);p.add_argument('--combo',required=True);p.add_argument('--out',required=True);a=p.parse_args()
plan=json.load(open(a.plan));uses=plan['clock']['landing_network']['start_tree']['uses'];parts={q['name']:q for q in plan['partitions']};types=plan['partition_types'];kit=Path(a.kit);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
v=Path(a.combo).read_text();by=collections.defaultdict(list);required=collections.defaultdict(dict)
for u in uses:
 part=parts[u['part']];tn=part['type'];pins={q['name']:q for q in types[tn]['clock']['landing_contract']['pins']};q=pins[u['pin']];assert q['dir'] in ['in','out'];assert re.fullmatch(r'[A-Za-z_]\w*',u['net']);by[u['part']].append(u);required[tn][u['pin']]=q
# LEF pin rectangles use the established landing_route/abstract_lef generator dimensions.
for tn,pins in required.items():
 part=next(n for n in by if parts[n]['type']==tn);m=re.search(r'(?m)^\s*(\S+)\s+'+re.escape(part)+r'\s*\(',v);assert m,part;mod=m.group(1);f=kit/'abstracts'/(mod+'.lef');s=f.read_text();add=[]
 for name,q in sorted(pins.items()):
  assert not re.search(r'^  PIN '+re.escape(name)+r'\s*$',s,re.M),'already has native landing pin'
  x,y=q['xy_um'];direction='INPUT' if q['dir']=='in' else 'OUTPUT';add.extend([f'  PIN {name}',f'    DIRECTION {direction} ;','    USE SIGNAL ;','    PORT',f'      LAYER {q["layer"]} ;',f'      RECT {x-.04:.6f} {y-.216:.6f} {x+.04:.6f} {y+.216:.6f} ;','    END',f'  END {name}'])
 marker='END '+mod;assert s.count(marker)==1;s=s.replace(marker,'\n'.join(add)+'\n'+marker);f.write_text(s)
for part,uu in by.items():
 pat=r'(?m)^(\s*\S+\s+'+re.escape(part)+r'\s*\()(.*?)(\);)';m=re.search(pat,v);assert m,part;assert all('.'+u['pin']+'(' not in m.group(2) for u in uu)
 extra=', '.join('.'+u['pin']+'('+u['net']+')' for u in uu);v=v[:m.start()]+m.group(1)+m.group(2)+', '+extra+m.group(3)+v[m.end():]
wires='\n'.join('  wire '+u['net']+';' for u in uses);assert len({u['net'] for u in uses})==len(uses)
pos=v.index('\n',v.index('module die_combo '))+1;v=v[:pos]+wires+'\n'+v[pos:];(out/'combo.v').write_text(v)
receipt=dict(schema='ot_native_start_source_endpoints/1',parts=len(by),types=len(required),endpoints=len(uses),inputs=sum(u['pin']=='cland_tstart_in' for u in uses),outputs=sum(u['pin']!='cland_tstart_in' for u in uses),scope='Exact plan-declared partition interface abstracts, not measured internal flop timing',uses=uses)
(out/'native_endpoints.json').write_text(json.dumps(receipt,indent=1)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k!='uses'}))
