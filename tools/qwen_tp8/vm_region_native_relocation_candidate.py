import json,re
from pathlib import Path
R=Path(__file__).resolve().parents[2];p=json.load(open(R/'results/arch/qwen_tp8_1012/vm_rg6.json'));s=json.load(open(R/'physical/ref_tile/qfd_vm_rg6.spec.json'));C={n:dict(c) for n,c in zip(p['core_names'],s['children'][:72])}
updates={**{f'b{i}_ctl':[69.12,23.76+i*205.2] for i in range(4)},'b4_in':[518.4,4.32],'b5_in':[518.4,71.28],'b6_in':[518.4,138.24],'b7_in':[518.4,984.96],'b5_ctl':[762.48,138.24],'b6_ctl':[762.48,179.28],'b7_ctl':[779.76,1034.64],'su0_in':[967.68,88.56],'su0_ctl':[967.68,6.48],'su1_in':[967.68,155.52],'su1_ctl':[967.68,47.52],'su2_in':[967.68,937.44],'su2_ctl':[967.68,1004.4],'su3_ctl':[1121.04,1019.52],'su4_ctl':[779.76,993.6]}
for n,at in updates.items():C['vm_g6_'+n]['at']=at
children=list(C.values())+s['children'][72:];boxes=[]
for c in children:
 t=next((R/c['view']).glob('*.lef')).read_text();w,h=map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',t).groups());x,y=c['at'];boxes.append((x,y,x+w,y+h,c['inst']))
coll=[]
for i,(x,y,X,Y,n) in enumerate(boxes):
 for bx,by,BX,BY,m in boxes[i+1:]:
  if x<BX+2.16-1e-6 and X>bx-2.16+1e-6 and y<BY+2.16-1e-6 and Y>by-2.16+1e-6:coll.append((n,m))
a=dict(schema='opentallas.vm-native-epoch-relocation-candidate.v1',claim='Proposedexistingclosedmasterrelocations ONLY, noRTLcyclechange. Boundingbox2.16channelcheck; requiresexactIOpinpacking, percornerETM internalwire budgets androute.',updates=updates,channel_defects=coll,children=children);(R/'results/arch/qwen_tp8_1012/rg6_native_epoch_relocation_candidate.json').write_text(json.dumps(a,indent=1)+'\n');print('defects',len(coll));print(coll[:40])

import json,re,hashlib,collections
from pathlib import Path
R=Path(__file__).resolve().parents[2];p=json.loads((R/'results/arch/qwen_tp8_1012/vm_rg6.json').read_text());spec=json.loads((R/'physical/ref_tile/qfd_vm_rg6.spec.json').read_text());W,H=p['outline_um'];children={c['inst']:c for c in spec['children']};cache={}
def pin(c,n):
 v=c['view']
 if v not in cache:
  f=next((R/v).glob('*.lef'));txt=f.read_text();pins={}
  for m in re.finditer(r'\bPIN\s+(\S+)(.*?)\n\s*END\s+\1\s',txt,re.S):
   rect=re.search(r'RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)',m[2]);
   if rect:
    x1,y1,x2,y2=map(float,rect.groups());pins[m[1]]=[(x1+x2)/2,(y1+y2)/2]
  cache[v]=pins
 xy=cache[v][n];return [xy[0]+c['at'][0],xy[1]+c['at'][1]]
def depths(xy):
 x,y=xy;return dict(w=x,e=W-x,s=y,n=H-y)

a=json.load(open(R/'results/arch/qwen_tp8_1012/rg6_native_epoch_relocation_candidate.json'));new={c['inst']:c for c in a['children']};names=dict(zip(p['core_names'],[c['inst'] for c in p['children'][:72]]));rows=[];missing=[]
for n,m in p['boundary_inputs'].items():
 pre=n.split('_')[0];chs=[new[names[m['child']]]] if m['child'] in names else [c for c in new.values() if c['inst'].startswith('u_'+m['child']+'_t')];nm={'rst':'rst_n','me':'me_in','wd':'d','swd':'d'}.get(pre,pre);xy=[]
 for c in chs:
  if m['child'] not in names:nm='me_e'
  for bit in range(m['bits']):
   try:xy.append(pin(c,nm if m['bits']==1 else f'{nm}[{bit}]'))
   except KeyError:missing.append((n,c['inst'],nm))
 if not xy:continue
 scores={f:max(depths(v)[f] for v in xy) for f in 'wesn'};f=min(scores,key=scores.get);rows.append(dict(port=n,bits=m['bits'],best_face=f,max_min_wire_um=scores[f],estimated_wire_ps=scores[f]*.76,child=m['child']))
a['input_screen']=rows;a['screen_missing_pins']=missing;a['remaining_wire_only_gt190_bits']=sum(x['bits'] for x in rows if x['estimated_wire_ps']>190);a['remaining_wire_only_gt190_ports']=[x for x in rows if x['estimated_wire_ps']>190];(R/'results/arch/qwen_tp8_1012/rg6_native_epoch_relocation_candidate.json').write_text(json.dumps(a,indent=1)+'\n');print('missing',missing[:8]);print('badbits',a['remaining_wire_only_gt190_bits']);print(a['remaining_wire_only_gt190_ports'])

a=json.load(open(R/'results/arch/qwen_tp8_1012/rg6_native_epoch_relocation_candidate.json'));C=dict(zip(p['core_names'],a['children'][:72]));rows=[]
def edge(src,sp,dst,dp,count=1,so=0,do=0):
 ss=C['vm_g6_'+src];dd=C['vm_g6_'+dst];ds=[]
 for i in range(count):
  sn=sp if count==1 and so==0 else f'{sp}[{so+i}]';dn=dp if count==1 and do==0 else f'{dp}[{do+i}]';
  try:sx,sy=pin(ss,sn)
  except KeyError:sx,sy=pin(ss,sn+'[0]')
  try:dx,dy=pin(dd,dn)
  except KeyError:dx,dy=pin(dd,dn+'[0]')
  ds.append(abs(sx-dx)+abs(sy-dy))
 rows.append(dict(source=src,source_pin=sp,target=dst,target_pin=dp,bits=count,maximum_manhattan_um=max(ds),mean_manhattan_um=sum(ds)/len(ds),screen_gt500_bits=sum(d>500 for d in ds)))
for i in range(8):
 edge(f'b{i}_in','q',f'b{i}','wd',512)
 for k,n in [('re',1),('we',1),('ra',8),('wl',8),('wm',16)]:edge(f'b{i}_ctl','m_'+k,f'b{i}',k,n)
 edge(f'b{i}_ctl','rtg',f'b{i}','rst_n')
 edge(f'b{i}','q',f'b{i}_bx','d',512)
 for j in range(2):
  for k in ['rtg','pgw','xg']:edge(f'b{i}_ctl',k,f'b{i}_xf{j}',k)
  edge(f'b{i}_bx','q',f'b{i}_xf{j}','bx',256,so=j*256)
for i in range(6):
 edge(f'su{i}_in','q',f'su{i}','swd',512)
 for k,n in [('sre',1),('swe',1),('sra',10),('swl',10),('swm',16)]:edge(f'su{i}_ctl','m_'+k,f'su{i}',k,n)
 edge(f'su{i}_ctl','rtg',f'su{i}','rst_n')
 for k in ['rtg','svc']:
  if i%2==0:edge(f'su{i}_ctl',k,'ans'+str(i//2),k)
 edge(f'su{i}','q','ans'+str(i//2),'sx',512,do=(i%2)*512)
# rr4 fixed bank bx mapping andrr2 stagedrowinputs.
for i in range(8):edge(f'b{i}_bx','q','rr4_'+str(i//4),'bx',512,do=(i%4)*512)
for h in range(2):edge('rr4_'+str(h),'t1','rr2','t1'+('a' if h==0 else 'b'),512)
a['internal_geometry_screen']=rows;a['internal_geometry_claim']='ActualclosedLEFpincenters Manhattanlowerbound ONLY, notroutedwire/percornerETMtimingproof. >500 islegacygeometric flag, notnew flatwirebudget.';(R/'results/arch/qwen_tp8_1012/rg6_native_epoch_relocation_candidate.json').write_text(json.dumps(a,indent=1)+'\n');print('pairs',len(rows),'gt500bits',sum(x['screen_gt500_bits'] for x in rows));print(sorted(rows,key=lambda x:-x['maximum_manhattan_um'])[:12])
