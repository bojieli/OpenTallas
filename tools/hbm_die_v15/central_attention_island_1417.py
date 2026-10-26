import json,copy
p=json.load(open('results/arch/hbm_die_v15/compact660_v5/compact.P.json'));W,H=31018.4,21277.693
out={k:v for k,v in p.items() if k.startswith('phy_')}
x0=(W-(3*6609.6+2*1100))/2
locations=[]
for c,count in [(0,10),(1,12),(2,10)]:
 y0=(H-(count*1712.08+(count-1)*20))/2
 for r in range(count):locations.append((c,r,x0+c*7709.6,y0+r*1732.08))
# Each source stack retains eight mapped SM owners; take contiguous half-panels.
for q,side,north in [('SW',0,False),('SE',2,False),('NW',0,True),('NE',2,True)]:
 ls=[z for z in locations if z[0]==side and ((z[1]>=5)==north)]
 mid=[z for z in locations if z[0]==1 and ((z[1]>=6)==north)]
 ls+=mid[:3] if side==0 else mid[3:]
 for n,(_,_,x,y) in enumerate(ls):out[f'sm_{q}{n}']={**p[f'sm_{q}{n}'],'x':x,'y':y}
for qi,q in enumerate(['SW','SE','NW','NE']):
 members=[v for k,v in out.items() if k.startswith('sm_'+q)]
 cy=sum(v['y']+v['h']/2 for v in members)/8
 cx=x0+6609.6+(7709.6 if qi%2 else 0)
 out['coll_'+q]={**p['coll_'+q],'x':cx+(1100-p['coll_'+q]['w'])/2,'y':cy-p['coll_'+q]['h']/2}
original=copy.deepcopy(p)
for q in ['SW','SE','NW','NE']:
 for n in range(4):del p[f'sfu_{q}{n}']
 p[f'SFUgroup_{q}']={'x':original[f'sfu_{q}0']['x'],'y':original[f'sfu_{q}0']['y'],'w':1020,'h':1620,'orient':'R0'}
free=[(20,20,W-40,H-40)]
def split(r,b):
 x,y,w,h=r;X,Y,U,V=b
 if x>=X+U or x+w<=X or y>=Y+V or y+h<=Y:return [r]
 a=[]
 if x<X:a.append((x,y,X-x,h))
 if x+w>X+U:a.append((X+U,y,x+w-X-U,h))
 if y<Y:a.append((x,y,w,Y-y))
 if y+h>Y+V:a.append((x,Y+V,w,y+h-Y-V))
 return a

def insert(b):
 global free
 nf=[t for r in free for t in split(r,b) if t[2]>1 and t[3]>1];free=[r for i,r in enumerate(nf) if not any(i!=j and r[0]>=s[0] and r[1]>=s[1] and r[0]+r[2]<=s[0]+s[2] and r[1]+r[3]<=s[1]+s[3] and (r!=s or i<j) for j,s in enumerate(nf))]
for v in out.values():insert((v['x']-10,v['y']-10,v['w']+20,v['h']+20))
graph=json.load(open('results/arch/hbm_die_v15/compact660_v5/compact.graph.json'))
def gap(a,b):return max(0,a['x']-b['x']-b['w'],b['x']-a['x']-a['w'])+max(0,a['y']-b['y']-b['h'],b['y']-a['y']-a['h'])
def cost(k,x,y,v):
 name=k.replace('SFUgroup_','sfu_')
 edges=[e for e in graph['links'] if e['src']==k or e['dst']==k or k.startswith('SFUgroup_') and (e['src'].startswith(name) or e['dst'].startswith(name))]
 total=0;ws=0
 for e in edges:
  other=e['dst'] if e['src']==k or k.startswith('SFUgroup_') and e['src'].startswith(name) else e['src']
  if other in out:total+=e['bits']*gap({'x':x+10,'y':y+10,'w':v['w'],'h':v['h']},out[other]);ws+=e['bits']
 return total/ws if ws else abs(x-v['x'])+abs(y-v['y'])
remaining=sorted((k for k in p if k not in out),key=lambda k:p[k]['w']*p[k]['h'],reverse=True)
fail=[]
for k in remaining:
 v=p[k];w,h=v['w']+20,v['h']+20;opts=[]
 for x,y,rw,rh in free:
  if rw>=w and rh>=h:
   for X,Y in [(x,y),(x+rw-w,y),(x,y+rh-h),(x+rw-w,y+rh-h)]:opts.append((cost(k,X,Y,v),rw*rh-w*h,X,Y))
 if not opts:fail.append(k);continue
 _,_,x,y=min(opts);out[k]={**v,'x':x+10,'y':y+10};insert((x,y,w,h))
for q in ['SW','SE','NW','NE']:
 v=out.pop(f'SFUgroup_{q}')
 for n in range(4):out[f'sfu_{q}{n}']={**original[f'sfu_{q}{n}'],'x':v['x']+(n%2)*520,'y':v['y']+(n//2)*820}
from pathlib import Path
import math,hashlib,collections
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
base=Path('results/arch/hbm_die_v15/central_attention_1417');base.mkdir(parents=True,exist_ok=True)
def metrics(P):
 overlaps=[];outside=[]
 for i,(k,a) in enumerate(P.items()):
  if a['x']<0 or a['y']<0 or a['x']+a['w']>W or a['y']+a['h']>H:outside.append(k)
  for j,(l,b) in enumerate(P.items()):
   if j>i and a['x']<b['x']+b['w'] and b['x']<a['x']+a['w'] and a['y']<b['y']+b['h'] and b['y']<a['y']+a['h']:overlaps.append([k,l])
 cls={}
 for e in graph['links']:
  a,b=P[e['src']],P[e['dst']];length=gap(a,b)/1000
  v=cls.setdefault(e['cls'],{'links':0,'bits_mm':0,'maximum_outline_gap_mm':0,'qwen_byte_mm':0,'ds_byte_mm':0})
  v['links']+=1;v['bits_mm']+=length*e['bits'];v['maximum_outline_gap_mm']=max(v['maximum_outline_gap_mm'],length)
  for name in ['qwen','ds']:v[name+'_byte_mm']+=length*e['bytes_per_token'].get(name,0)
 attention=[]
 for q in ['SW','SE','NW','NE']:
  root=P['coll_'+q]
  for n in range(8):
   a=P[f'sm_{q}{n}'];attention.append(gap(a,root)/1000)
 return {'overlaps':overlaps,'outside':outside,'unplaced':[k for k in original if k not in P],'class_metrics':cls,'total_bits_mm':sum(v['bits_mm'] for v in cls.values()),'SM_to_existing_COLL_placeholder_outline_gap_mm':{'max':max(attention),'mean':sum(attention)/len(attention)},'attention_metric_is_actual_624lane_graph':False}
assert len(out)==195 and not fail
M={'schema':'opentallas.hbm.central-attention-placement-screen.v1','die_mm2':660,'die_um':[W,H],'carried_envelope_mm2':sum(v['w']*v['h'] for v in original.values())/1e6,'new_service_macros_die':576,'dualprogramme_additional_macros_die':32,'dedicated_PV_additional_macros_die':64,'additional_source_area_reconciliation':'OPEN: native576 service SRAM includes32 existing programme macros; cannot add or absorb areas until old SM/PC source hierarchy is reconciled. New sources are not spatially assigned in either comparison.','planning_graph_links':len(graph['links']),'source_graph_binding_status':'These709 planning links are NOT current83-instance695-edge source graph; SM_HBM formatted packet shortcut and SM_X collapsed provenance remain unbound.','source_current_full_die_GRT':'BLOCKED missing actual source-specific masters/views; no unchanged full route retry.','variants':{'stack_local_baseline':metrics(original),'central_3column_island':metrics(out)},'qualified':False,'winner':None,'fixed_roots_phase_PG_pin_cuts':'OPEN both alternatives; no clock insertion/PG waiver or extra feedthrough capacity assumed','constraints':['Original PHY outlines and positions retained','Every195 carried master rectangle retained with no90degree rotation','32 SM arranged three columns10/12/10; 1100um central corridors','Four SFU groups each four500x800 leaves arranged2x2 with20um internal gaps; native remote-bank source transport still required','Eight actual source PC owners grouped per stack unchanged; all709 carried incident links measured','Four existing COLL envelopes placed in island corridors as placeholders; actual624-adder tree/stager source footprints not inherited','660mm2 retained; no growth claimed','SM frames and all carried outlines are historical envelopes, not physical adoption of new producers/consumers'],'open':['Actual624-lane ordered tree graph and relay edges required','Actual native service/cache/stager placement with all576/608/672 macro alternatives reconciled','32SM actual arithmetic command producer and two-word protected programme source join','Exact pins, clock entries, PG cuts, halo, feedthrough FF home and route area','All source-current unresolved ports remain unresolved unless actual RTL connection is published']}
for k,v in M['variants'].items():assert not v['overlaps'] and not v['outside'] and not v['unplaced'],(k,v['overlaps'],v['outside'])
(base/'central.P.json').write_text(json.dumps(out,indent=1)+'\n');(base/'comparison.json').write_text(json.dumps(M,indent=1)+'\n')
colors={'phy':'#bbddee','sm':'#97c894','pc':'#e4bc74','idx':'#cbb4dd','vmb':'#edcae0','vmh':'#dba2ca','su':'#f0e070','sucore':'#d5c34e','sfu':'#f4b4a5','coll':'#91cfe0','hc':'#d7d7d7','dbk':'#dea566','lk':'#a0a0a0','ep':'#c0c0c0','quant':'#cab187'}
fig,axes=plt.subplots(1,2,figsize=(26,11))
for ax,(title,P) in zip(axes,[('Stack-local baseline: carried envelopes',original),('Central attention island: carried envelopes',out)]):
 for k,v in P.items():
  c=colors.get(k.split('_')[0],'#ddd');ax.add_patch(Rectangle((v['x']/1000,v['y']/1000),v['w']/1000,v['h']/1000,facecolor=c,edgecolor='#333',linewidth=.4))
  ax.text((v['x']+v['w']/2)/1000,(v['y']+v['h']/2)/1000,k.replace('_',' '),ha='center',va='center',fontsize=4 if v['w']<800 else 6,rotation=90 if v['h']>2*v['w'] else 0)
 for q in ['SW','SE','NW','NE']:
  root=P['coll_'+q]
  for n in range(8):
   a=P[f'sm_{q}{n}'];ax.plot([(a['x']+a['w']/2)/1000,(root['x']+root['w']/2)/1000],[(a['y']+a['h']/2)/1000,(root['y']+root['h']/2)/1000],color='#075f93',alpha=.4,linewidth=.55,linestyle='--')
 ax.set(xlim=(0,W/1000),ylim=(0,H/1000),xlabel='mm',ylabel='mm',title=title);ax.set_aspect('equal');ax.grid(alpha=.15)
fig.suptitle('660 mm² global placement comparison — source joins and physical views remain OPEN',fontsize=17)
fig.text(.5,.04,'Dashed lines: SM to existing COLL envelope only, not the actual 624-lane ordered tree. All 709 incident planning links are measured in comparison.json.\nNew native service 576 SRAM/die; dual programme +32; dedicated PV stagers +64. Area replacement and all clocks / PG / pin cuts remain unassigned.',ha='center',fontsize=11)
fig.tight_layout(rect=[0,.09,1,.95]);fig.savefig(base/'placement.svg');fig.savefig(base/'placement.png',dpi=170)
print(json.dumps({k:{'total_bits_mm':v['total_bits_mm'],'attention_proxy':v['SM_to_existing_COLL_placeholder_outline_gap_mm']} for k,v in M['variants'].items()},indent=1))
