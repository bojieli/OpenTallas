#!/usr/bin/env python3
"""Bind 96 real ECTL views into split system candidate; audit five exact RTL seams."""
import gzip,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'results/arch/qwen_split_feasibility_1013'
sys.path.insert(0,str(ROOT/'tools/hier_contract'))
import pair_check as P
masters=json.loads((OUT/'ectl_closed_masters.json').read_text());table=P.load_table(OUT/'ectl_closed_timing.json');leaves={}
for master,view in masters.items():
 p=ROOT/view/(master+'.lef');s=p.read_text();w,h=map(float,re.search(r'SIZE\s+(\S+)\s+BY\s+(\S+)',s).groups());pins={}
 for m in re.finditer(r'^\s*PIN\s+(\S+)\s*$(.*?)^\s*END\s+\1\s*$',s,re.M|re.S):
  r=re.search(r'LAYER\s+(\S+)\s*;\s*RECT\s+([-\d. ]+)\s*;',m[2])
  if r:
   x0,y0,x1,y1=map(float,r[2].split());pins[m[1]]=[(x0+x1)/2,(y0+y1)/2,r[1]]
 leaves[master]=dict(w=w,h=h,pins=pins,lef_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),view_source_hashes={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in (ROOT/view).iterdir() if f.is_file() and (f.suffix in ('.lib','.lef') or f.name=='insertion.json')})
parent=json.loads((OUT/'partial_system_packing.json').read_text());rects=[];seams=[];missing=[];Pdie=P.Die(table,{})
for old in parent['positions']:
 if old['m']!='qkd_ectl':rects.append(old);continue
 _,stack,engine=old['n'].split('_');engine=int(engine);col=engine//4 if stack[0]=='W' else 1-engine//4
 orient='R0' if col==0 else 'MY';parts={};offset=0
 for suffix in 'abc':
  master='qkd_ectl_'+suffix;l=leaves[master];x=old['x']+(648-offset-l['w'] if orient=='MY' else offset)
  parts[suffix]=dict(n=old['n']+'_'+suffix,m=master,x=x,y=old['y'],w=l['w'],h=l['h'],orient=orient,cfg=(engine<<2)+('WS','WN','ES','EN').index(stack),view=masters[master],lef_sha256=l['lef_sha256']);offset+=l['w'];rects.append(parts[suffix])
 for a,ap,b,bp,n in [('a','rs_o','b','rs_i',513),('a','rvm_o','b','rvm_i',1),('b','x_o','a','x_i',52),('c','x_o','b','x_i',52),('b','rsv_o','c','rsv_i',1)]:
  aa,bb=parts[a],parts[b]
  for bit in range(n):
   pa=ap+f'[{bit}]' if n>1 else ap;pb=bp+f'[{bit}]' if n>1 else bp
   if pa not in leaves[aa['m']]['pins'] or pb not in leaves[bb['m']]['pins']:missing.append([aa['n'],pa,bb['n'],pb]);continue
   ax,ay,_=leaves[aa['m']]['pins'][pa];bx,by,_=leaves[bb['m']]['pins'][pb]
   if orient=='MY':ax=aa['w']-ax;bx=bb['w']-bx
   length=abs(aa['x']+ax-bb['x']-bx)+abs(ay-by)
   verdict=P.check(Pdie,dict(a=(aa['n'],aa['m'],pa),b=(bb['n'],bb['m'],pb),um=length))
   seams.append(dict(a=[aa['n'],pa],b=[bb['n'],pb],um=round(length,6),tt_ff_pair=verdict))
overlap=[]
for j,p in enumerate(rects):
 for q in rects[j+1:]:
  if p['x']<q['x']+q['w']-1e-6 and q['x']<p['x']+p['w']-1e-6 and p['y']<q['y']+q['h']-1e-6 and q['y']<p['y']+p['h']-1e-6:overlap.append([p['n'],q['n']])
r=dict(status='96_REAL_ECTL_VIEW_BINDINGS_COMPONENT_AUDIT_NOT_RELEASE',positions=rects,ectl_leaf_count=sum(p['m'] in masters for p in rects),
 overlaps=overlap,seam_bit_count=len(seams),missing_pin_pairs=missing,max_seam_um=max(s['um'] for s in seams),
 timing_counts={k:sum(s['tt_ff_pair']['status']==k for s in seams) for k in ('pass','fail','hold','unmeasured')},seams=seams,
 missing=['Exact source cfg straps use current qkd_ectl3 mapping; full system netlist external head/controller seams and timing absent.',
 'Orientation inherited from current kv_die.py engine-column rule; complete mirrored-source placement contract must still be regenerated.',
 'Physical clock phi-R entry wiring, SS internal timing and actual routed cuts remain absent.',
 'PG/signal lattice phase must be legalized for translated outlines before physical placement.'])
r['view_source_hashes']={k:v['view_source_hashes'] for k,v in leaves.items()};gzip.open(OUT/'system_96_ectl_bindings.json.gz','wt').write(json.dumps(r)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ('positions','seams','missing')},indent=2))
