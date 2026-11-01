from pathlib import Path
import json,re,subprocess,sys
r=Path(__file__).resolve().parent;sys.path.insert(0,'/srv/opentallas-scratch/claude/wt/codex-hbm-clock-sparse/tools/die_plan')
import schema as S,die_trial as DT
P=S.Plan(S.load(r/'current_C11E_plan.json'));sm=DT.SiteMap(P,halo=4.32);j=json.load(open(r/'NE_pilot.json'));origin=(15042.24,6065.28)
base=r/'joint_base.def';subprocess.run([sys.executable,str(r/'crop2.py'),str(r/'NE_pilot.def'),str(base),'3500','400','4900','950'],check=True)
v=(r/'joint_synth/native.v').read_text();ffs=re.findall(r'(DFF\w+)\s+(\w+)\s*\(\s*\.CLK\(clk\)',v);assert len(ffs)==3,ffs
orig=(r/'feed_ne_actual_b_new_r2/pilot.def').read_text()
def body(s,name):return re.search(rf'(?ms)^{name} \d+ ;\n(.*?)^END {name}',s)[1].strip().splitlines()
def repl(s,name,rows):return re.sub(rf'(?ms)^{name} \d+ ;.*?^END {name}',f'{name} {len(rows)} ;\n'+'\n'.join(rows)+f'\nEND {name}',s)
for variant,p2 in [('north',[4402.944,657.45]),('east',[4471.92,631.8])]:
 out=r/f'joint_NE_B_{variant}';out.mkdir(exist_ok=True);s=base.read_text();cs=body(orig,'COMPONENTS');pos={}
 for ln in cs:
  m=re.match(r'- (\S+) (\S+).*?\( (\d+) (\d+) \)',ln);pos[m[1]]=(int(m[3])/1000,int(m[4])/1000)
 prefix=['R','P1','P2','P3']+[f'XI{i}' for i in range(8)]
 for n in prefix:
  c=j['cells'][n];xy=p2 if n=='P2' else [4688.226,696.33] if n=='P3' else [c['x'],c['y']];pos[n]=xy
  cs.append(f'- {n} {c["master"]} + FIXED ( {round(xy[0]*1000)} {round(xy[1]*1000)} ) N ;')
 stage=[]
 for i,(master,name) in enumerate(ffs):
  n='start_'+name;xy=[p2[0]+2.16+i*1.08,p2[1]];pos[n]=xy;stage.append(n);cs.append(f'- {n} {master} + FIXED ( {round(xy[0]*1000)} {round(xy[1]*1000)} ) N ;')
 s=repl(s,'COMPONENTS',cs)
 pins=[ln for ln in body(orig,'PINS') if not ln.startswith('- mesh_root ')];s=s.replace('COMPONENTS',f'PINS {len(pins)} ;\n'+'\n'.join(pins)+'\nEND PINS\nCOMPONENTS',1)
 ns=[ln.replace('( PIN mesh_root )','( R A )') for ln in body(orig,'NETS')]
 for nn in ['n_R','n_P1','n_P2']:
  n=j['nets'][nn];pairs=f'( {n["drv"]} Y ) '+' '.join(f'( {c} A )' for c in n['loads'])
  if nn=='n_P2':pairs+=' '+' '.join(f'( {c} CLK )' for c in stage)
  ns.append(f'- {nn} {pairs} + USE CLOCK ;')
 s=repl(s,'NETS',ns)
 # Lower layers are reserved except declared local pin-access windows. New C11E core outlines remain obstacles.
 x0,y0,x1,y1=3500,400,4900,950
 windows=[(x-1.5,y-1.5,x+3.12,y+1.77) for x,y in pos.values()]
 ys=sorted({y0,y1}|{max(y0,min(y1,z)) for a,b,c,d in windows for z in (b,d)})
 bl=[]
 for ya,yb in zip(ys,ys[1:]):
  gaps=[]
  for a,b,c,d in windows:
   if b<(ya+yb)/2<d:gaps.append((max(x0,a),min(x1,c)))
  gaps.sort();merged=[]
  for a,b in gaps:
   if merged and a<=merged[-1][1]:merged[-1][1]=max(merged[-1][1],b)
   else:merged.append([a,b])
  cuts=[];xx=x0
  for a,b in merged:
   if a>xx:cuts.append((xx,a))
   xx=max(xx,b)
  if xx<x1:cuts.append((xx,x1))
  for a,b in cuts:
   for layer in range(2,8):bl.append(f'- LAYER M{layer} RECT ( {round(a*1000)} {round(ya*1000)} ) ( {round(b*1000)} {round(yb*1000)} ) ;')
 cores=[]
 for part,pa in P.parts.items():
  typ=P.types[pa['type']]
  for c in typ.get('hard_cores',[]):
   x,y=c['origin_um'];w,h=c['outline_um'];a,b=P.to_die(part,(x,y)),P.to_die(part,(x+w,y+h));box=[min(a[0],b[0])-origin[0],min(a[1],b[1])-origin[1],max(a[0],b[0])-origin[0],max(a[1],b[1])-origin[1]]
   if box[2]<x0 or box[0]>x1 or box[3]<y0 or box[1]>y1:continue
   cores.append(dict(inst=part+'/'+c['inst'],rect_um=box))
   for layer in range(1,6):bl.append(f'- LAYER M{layer} RECT ( {round(max(x0,box[0])*1000)} {round(max(y0,box[1])*1000)} ) ( {round(min(x1,box[2])*1000)} {round(min(y1,box[3])*1000)} ) ;')
 s=repl(s,'BLOCKAGES',bl);(out/'pilot.def').write_text(s)
 illegal=[]
 for n,(x,y) in pos.items():
  if not all(sm.legal((x+origin[0]+dx,y+origin[1]+dy)) for dx,dy in [(0,0),(1.08 if n.startswith("start_") else 1.62,.27)]):illegal.append(n)
 assert not illegal,illegal
 legs=[dict(net=nn,src=n['drv'],dst=c,length_um=abs(pos[n['drv']][0]-pos[c][0])+abs(pos[n['drv']][1]-pos[c][1])) for nn,n in j['nets'].items() if nn in ['n_R','n_P1','n_P2'] for c in n['loads']]
 assert max(z['length_um'] for z in legs)<405
 scope=dict(variant=variant,positions=pos,cores=cores,legs=legs,required_core_halo_um=4.32,stage_native_masters=ffs,stage_cells=stage,stage_scope='actual PAD0 EDGE_FALL0 origin three native mapped FF CLK loads; data/reset logic excluded from this clock-only probe',original_geometry='C12e original R/P1/XI inputs retained; P2/P3 moved for actual C11E core exclusions',G4='BLOCKED full clock/mesh/signals/reset integration',root_pin_removed='restoring output connects directly to actual R/A')
 (out/'scope.json').write_text(json.dumps(scope,indent=2));print(variant,len(cs),'cells',len(ns),'nets',max(z['length_um'] for z in legs),'maxleg')
