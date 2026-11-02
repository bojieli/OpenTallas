from pathlib import Path
import json,re,collections
import geom_rules as G
R=Path(__file__).resolve().parent;D=G.Design(R/'complete_model.tsv')
source=json.loads((R/'native_reset_source_graph.json').read_text())
byname={c[-1]:i for i,c in D.cells.items()}
terminals={}
for q,tree in source.items():
 name='u_bound.'+tree['path'][0]['instance']+'/q$_DFF_P_';assert name in byname
 i=byname[name];terminals[i]=dict(logical=q,name=name,xy=list(G.ctr(D.cells[i])),clock='clk',root=tree['root'],depth=tree['depth'])
def driver(net,trail=(),parity=0):
 if net in trail:return None
 dr=D.nets[net][1]
 if not dr:return None
 if dr[0]=='p':return dict(kind='port',pin=D.pin_by_k[dr[1]]['name'],trail=list(trail))
 i=dr[1];c=D.cells[i]
 if c[0]=='S':return dict(kind='FF',id=i,name=c[-1],parity=parity,trail=list(trail))
 if c[0] not in ('B','K'):return None
 ins=[n for n,ck in D.cell_in.get(i,[])]
 if len(ins)!=1:return None
 return driver(ins[0],trail+(net,),parity^int(c[1].startswith('INV')))
clocks=[p for p in D.pins if re.fullmatch(r'clk(?:_t\d+)?',p['name'])]
clock_rows=[];unknown=[];loads=collections.Counter()
for i,c in D.cells.items():
 if c[0]!='S':continue
 cn=[n for n,ck in D.cell_in.get(i,[]) if ck]
 if len(cn)!=1:unknown.append(dict(name=c[-1],reason='clock net count',count=len(cn)));continue
 dr=driver(cn[0])
 if not dr or dr['kind']!='port':unknown.append(dict(name=c[-1],reason='not a unique actual primary clock driver',driver=dr));continue
 x,y=G.ctr(c);old=dr['pin']
 if re.fullmatch(r'clk(?:_t\d+)?',old):
  p=min(clocks,key=lambda p:abs(p['x']-x)+abs(p['y']-y));new=p['name'];reason='existing same-domain nearest core-clock-tap rule; proposed only'
 else:
  assert old.startswith('fclk_in_'),old
  p=next(p for p in D.pins if p['name']==old);new=old;reason='preserve actual forwarded-clock source; never substitute core tap'
 loads[new]+=1
 clock_rows.append(dict(name=c[-1],xy=[x,y],actual_source=old,proposed_source=new,clock_xy=[p['x'],p['y']],reach_um=abs(p['x']-x)+abs(p['y']-y),reason=reason))
native=lambda n:any(s in n for s in ('u_bin_','u_bout_','u_ist_','u_u_efault.','u_u_fch.'))
reset_rows=[]
for i,c in D.cells.items():
 if c[0]!='S' or not native(c[-1]):continue
 for n,ck in D.cell_in.get(i,[]):
  if ck:continue
  dr=driver(n)
  if not dr or dr['kind']!='FF' or dr['id'] not in terminals:continue
  xy=G.ctr(c);j=min(terminals,key=lambda j:sum(abs(a-b) for a,b in zip(terminals[j]['xy'],xy)))
  old,new=terminals[dr['id']],terminals[j]
  assert old['clock']==new['clock']=='clk' and old['depth']==new['depth']==7 and old['root']==new['root']=='rst_root_n'
  reset_rows.append(dict(target=c[-1],input_net_index=n,old=old,new=new,actual_buffer_INV_parity=dr['parity'],target_xy=list(xy),new_reach_um=sum(abs(a-b) for a,b in zip(new['xy'],xy)),eligibility='actual direct BUF/INV-only terminal cone; source phase equality proved after7 edges; parent boot/START join HELD'))
out=dict(scope='PREP only, no physical clock/reset net rewire or gate credit. All source clocks resolved from actual mapped net graph; forwarded domains preserved.',clock_FFs=len(clock_rows),clock_unknown=unknown,clock_max=max(x['reach_um'] for x in clock_rows),clock_loads=dict(loads),clock_rows=clock_rows,reset_direct_eligible=reset_rows,parent_boot_START_join='HELD')
(R/'complete_clock_reset_manifest.json').write_text(json.dumps(out,indent=2))
print('clockFF',len(clock_rows),'unknown',len(unknown),'clockmax',out['clock_max'],'coremaxload',max(v for k,v in loads.items() if k.startswith('clk')))
print('reset direct eligible',len(reset_rows),'newresetmax',max(z['new_reach_um'] for z in reset_rows))
