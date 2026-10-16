import json,re,subprocess,hashlib,math
from pathlib import Path
from collections import defaultdict,Counter
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import argparse
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);args=p.parse_args()
R=Path(__file__).resolve().parents[3];O=args.out;O.mkdir(parents=True,exist_ok=True)
screen=json.loads((R/'results/arch/s81_mix4_localized_1016/connected_geometry/baseline_leaf_geometry.json').read_text());J=json.loads((O/'cluster_graph.json').read_text());top=J['modules']['ot_s81_engram_mixq_clocked_candidate'];cells=top['cells'];assert len(cells)==38
pins={};dims={};hashes={}
for key,v in screen['actual_leaf_views'].items():
 raw=subprocess.check_output(['git','show',v['record']+':'+v['path']],cwd=R);assert hashlib.sha256(raw).hexdigest()==v['sha256'];s=raw.decode();master='ot_s81_engram_'+key;dims[master]=v['outline_um'];pins[master]={};hashes[master]=v
 for m in re.finditer(r'^  PIN (\S+)\n(.*?)^  END \1$',s,re.M|re.S):
  name,body=m[1],m[2];shapes=[]
  for rect in re.finditer(r'RECT\s+([\d.e+-]+)\s+([\d.e+-]+)\s+([\d.e+-]+)\s+([\d.e+-]+)',body):
   a,b,c,d=map(float,rect.groups());shapes.append(((a+c)/2,(b+d)/2))
  pins[master][name]=shapes
# Actual elaborated wire graph, one concrete node for each real child.
# Stable association of previous geometric reservations to concrete RTL instances.
base={};short={}
for name in cells:
 if name=='shell.ctl':tag='shell2'
 elif m:=re.fullmatch(r'shell.col\[(\d+)\].u',name):tag='shell'+str([0,1,3,4][int(m[1])])
 elif m:=re.fullmatch(r'mix.g_mult\[(\d+)\].leaf',name):g=int(m[1]);tag=('mul4a'if g%2==0 else'mul4b')+str(g//2)
 elif m:=re.fullmatch(r'mix.g_add\[(\d+)\].leaf',name):tag='add8'+m[1]
 elif name=='mix.relay':tag='relay0'
 elif name=='mix.hsum':tag='chunkA3'
 elif name=='mix.ksum':tag='chunkB3'
 elif name=='mix.dsum':tag='chunkB4'
 elif name=='mix.g_norm[0].leaf':tag='scalar0'
 elif name=='mix.g_norm[1].leaf':tag='scalar4'
 elif name=='mix.control':tag='scalar2'
 elif name=='mix.gate_leaf.magnitude':tag='scalar1'
 elif name=='mix.gate_leaf.sigmoid':tag='scalar3'
 elif m:=re.fullmatch(r'mix.g_reduce\[(\d+)\].g_chunk\[(\d+)\].leaf',name):
  i=int(m[1])*4+int(m[2]);tag=(['chunkA0','chunkA1','chunkA2','chunkA4','chunkA5','chunkA6','chunkB0','chunkB1','chunkB2','chunkB5','chunkB6','chunkB7'])[i]
 else:raise ValueError(name)
 b=next(b for b in screen['cluster']['boxes']if b['name']==tag);assert dims[cells[name]['type']]==[b['w'],b['h']]
 base[name]={'x':b['x'],'y':876.96-b['y']-b['h'],'w':b['w'],'h':b['h']};short[name]=tag
assert len({tuple(b.items())for b in base.values()})==38
# E1: keep exact arithmetic rows; remove the shell strip, move shell/control into E column.
e1={}
for n,b in base.items():
 if n.startswith('shell.'):continue
 e1[n]={**b,'y':b['y']}
for c in range(4):
 n=f'shell.col[{c}].u';w,h=dims[cells[n]['type']];e1[n]={'x':898.56,'y':50+190*c,'w':w,'h':h}
n='shell.ctl';w,h=dims[cells[n]['type']];e1[n]={'x':898.56,'y':335,'w':w,'h':h}
# E2: four source-connected bands. unrotated chunk/add/mul/shell in each band.
e2={}
for c in range(4):
 y=801.36-(120.96+c*142.56)
 specs=[(f'mix.g_reduce[{r}].g_chunk[{c}].leaf',112.32*r)for r in range(3)]
 specs += [(f'mix.g_add[{c}].leaf',336.96),(f'mix.g_mult[{2*c}].leaf',540.0),(f'mix.g_mult[{2*c+1}].leaf',743.04),(f'shell.col[{c}].u',946.08)]
 for n,x in specs:
  w,h=dims[cells[n]['type']];e2[n]={'x':x,'y':y,'w':w,'h':h}
for n,x in [('mix.hsum',0),('mix.ksum',112.32),('mix.dsum',224.64),('mix.g_norm[0].leaf',336.96),('mix.g_norm[1].leaf',540),('mix.gate_leaf.magnitude',743.04)]:
 w,h=dims[cells[n]['type']];e2[n]={'x':x,'y':131.76,'w':w,'h':h}
for n,x in [('mix.control',0),('mix.gate_leaf.sigmoid',112.32),('mix.relay',315.36),('shell.ctl',946.08)]:
 w,h=dims[cells[n]['type']];e2[n]={'x':x,'y':0,'w':w,'h':h}
# E2 row0 bottom110.16, row1 begins131.76..231.12; rowbands start252.72 =>801.36.
q1={}
for c in range(4):
 ox=423.36*(c%2);oy=496.8*(c//2)
 for n,x,y in [(f'mix.g_reduce[{r}].g_chunk[{c}].leaf',112.32*r,0)for r in range(3)]+[(f'mix.g_add[{c}].leaf',0,112.32),(f'shell.col[{c}].u',203.04,112.32),(f'mix.g_mult[{2*c}].leaf',0,233.28),(f'mix.g_mult[{2*c+1}].leaf',203.04,233.28)]:
  w,h=dims[cells[n]['type']];q1[n]={'x':ox+x,'y':oy+y,'w':w,'h':h}
for n,x in [('mix.hsum',0),('mix.ksum',112.32),('mix.dsum',224.64),('mix.g_norm[0].leaf',336.96),('mix.g_norm[1].leaf',540),('shell.ctl',743.04)]:
 w,h=dims[cells[n]['type']];q1[n]={'x':x,'y':375.84,'w':w,'h':h}
for n,y in [('mix.gate_leaf.sigmoid',244.08),('mix.control',496.8),('mix.gate_leaf.magnitude',583.2),('mix.relay',648.0)]:
 w,h=dims[cells[n]['type']];q1[n]={'x':846.72,'y':y,'w':w,'h':h}
variants={'Q_central_reducers':(q1,[1028.16,851.04]),'N_inherited':(base,[876.96,876.96]),'E_side_shells':(e1,[1062.72,801.36]),'E_connected_bands':(e2,[1110.24,801.36])}
# Per-bit drivers and sinks with actual LEF terminal rectangles.
drivers=defaultdict(list);sinks=defaultdict(list);missing=[];excluded=Counter()
def endpoints(n,p,bitindex):
 cell=cells[n];master=cell['type'];conn=cell['connections'][p];pn=p if len(conn)==1 else f'{p}[{bitindex}]'
 if pn not in pins[master]:missing.append((n,pn));return None
 return (n,pn)
for n,cell in cells.items():
 for p,bits in cell['connections'].items():
  if p in ('ck','clk','rst','arst_n'):excluded[p]+=len(bits);continue
  for i,bit in enumerate(bits):
   if not isinstance(bit,int):continue
   ep=endpoints(n,p,i)
   if ep:(drivers if cell['port_directions'][p]=='output' else sinks)[bit].append(ep)
assert not missing,missing[:20]
joins=[];boundary=[]
for bit,ss in sinks.items():
 for sink in ss:
  if bit in drivers:
   assert len(drivers[bit])==1,(bit,drivers[bit]);joins.append((drivers[bit][0],sink))
  else:boundary.append(sink)
def coords(ep,boxes):
 n,p=ep;b=boxes[n];return [(b['x']+x,b['y']+y)for x,y in pins[cells[n]['type']][p]]
def dist(a,b,boxes):return min(abs(x-u)+abs(y-v)for x,y in coords(a,boxes)for u,v in coords(b,boxes))
# Optimize a central row of actual global leaves against the full bit graph.
import numpy as np,random
names=list(cells);index={n:i for i,n in enumerate(names)}
si=np.array([index[a[0]]for a,b in joins]);ti=np.array([index[b[0]]for a,b in joins]);so=np.array([pins[cells[a[0]]['type']][a[1]][0]for a,b in joins]);to=np.array([pins[cells[b[0]]['type']][b[1]][0]for a,b in joins])
globalrow=['mix.hsum','mix.ksum','mix.dsum','mix.g_norm[0].leaf','mix.g_norm[1].leaf','shell.ctl','mix.relay','mix.control']
def build(order):
 boxes={n:dict(b)for n,b in q1.items()};x=0
 for n in order:boxes[n].update(x=x,y=375.84);x+=boxes[n]['w']+21.6
 boxes['mix.gate_leaf.magnitude']['y']=496.8
 return boxes
def objective(boxes):
 xy=np.array([(boxes[n]['x'],boxes[n]['y'])for n in names]);d=np.abs(xy[si]+so-xy[ti]-to).sum(axis=1)
 return d.sum()+6*np.maximum(d-500,0).sum()+1000*d.max()
bestorder=globalrow[:];bestboxes=build(bestorder);bestcost=objective(bestboxes);rng=random.Random(217)
for seed in range(3):
 order=bestorder[:];cost=bestcost
 for step in range(3500):
  trial=order[:];i,j=rng.sample(range(8),2);trial[i],trial[j]=trial[j],trial[i];boxes=build(trial);v=objective(boxes);temperature=70000*(1-step/3500)+100
  if v<cost or rng.random()<math.exp(min(0,(cost-v)/temperature)):order,cost=trial,v
  if v<bestcost:bestorder,bestcost,bestboxes=trial,v,boxes
import itertools
capsule={n:dict(b)for n,b in bestboxes.items()}
def reach_score(boxes):
 xy=np.array([(boxes[n]['x'],boxes[n]['y'])for n in names]);d=np.abs(xy[si]+so-xy[ti]-to).sum(axis=1)
 return 10000*np.count_nonzero(d>500)+1000*d.max()+np.maximum(d-500,0).sum()+.1*d.sum()
for sweep in range(2):
 for c in range(4):
  ox=423.36*(c%2);oy=496.8*(c//2);bestlocal=capsule;localcost=reach_score(capsule)
  for roworder in itertools.permutations(['mul','mid','chunk']):
   yy={};cursor=0
   for tag in roworder:yy[tag]=cursor;cursor+={'mul':120.96,'mid':99.36,'chunk':90.72}[tag]+21.6
   for chunks in itertools.permutations(range(3)):
    for swapmul,swapmid in itertools.product(range(2),repeat=2):
     trial={n:dict(b)for n,b in capsule.items()}
     specs=[(f'mix.g_mult[{2*c+(k^swapmul)}].leaf',203.04*k,yy['mul'])for k in range(2)]
     specs +=[(f'mix.g_reduce[{r}].g_chunk[{c}].leaf',112.32*k,yy['chunk'])for k,r in enumerate(chunks)]
     specs +=[(f'shell.col[{c}].u',0 if swapmid else 203.04,yy['mid']),(f'mix.g_add[{c}].leaf',185.76 if swapmid else 0,yy['mid'])]
     for n,x,y in specs:trial[n].update(x=ox+x,y=oy+y)
     v=reach_score(trial)
     if v<localcost:bestlocal,localcost=trial,v
  capsule=bestlocal
# Final all-incident central-order refinement after quarter row permutations.
fixedcapsule={n:dict(b)for n,b in capsule.items()};order=bestorder[:]
def placecapsule(order):
 boxes={n:dict(b)for n,b in fixedcapsule.items()};x=0
 for n in order:boxes[n].update(x=x,y=375.84);x+=boxes[n]['w']+21.6
 return boxes
capsulebest=reach_score(capsule);current=order[:];currentcost=capsulebest
for step in range(7000):
 trial=current[:];i,j=rng.sample(range(8),2);trial[i],trial[j]=trial[j],trial[i];boxes=placecapsule(trial);v=reach_score(boxes);temperature=150000*(1-step/7000)+100
 if v<currentcost or rng.random()<math.exp(min(0,(currentcost-v)/temperature)):current,currentcost=trial,v
 if v<capsulebest:capsulebest,capsule=v,boxes
variants={'Q_cooptimized_capsules':(capsule,[1028.16,851.04]),'Q_optimized_center':(bestboxes,[1028.16,851.04]),**variants}
results={};overruns_by_variant={}
for tag,(boxes,outline)in variants.items():
 assert set(boxes)==set(cells)
 overlap=[];clearances=[]
 for n,b in boxes.items():
  assert b['x']>=0 and b['y']>=0 and b['x']+b['w']<=outline[0]+.001 and b['y']+b['h']<=outline[1]+.001,(tag,n,b,outline)
  for m,c in boxes.items():
   if n<m:
    dx=max(b['x']-c['x']-c['w'],c['x']-b['x']-b['w'],0);dy=max(b['y']-c['y']-c['h'],c['y']-b['y']-b['h'],0);clearances.append(dx+dy)
   if n<m and min(b['x']+b['w'],c['x']+c['w'])-max(b['x'],c['x'])>.001 and min(b['y']+b['h'],c['y']+c['h'])-max(b['y'],c['y'])>.001:overlap.append((n,m))
 assert not overlap,(tag,overlap)
 assert min(clearances)>=21.599,(tag,min(clearances))
 rows=[{'source':a,'sink':b,'minimum_L1_um':dist(a,b,boxes)}for a,b in joins];lengths=sorted(r['minimum_L1_um']for r in rows);groups=defaultdict(lambda:[0,0,0])
 for row in rows:
  key=row['source'][0]+' -> '+row['sink'][0];groups[key][0]+=1;groups[key][1]=max(groups[key][1],row['minimum_L1_um']);groups[key][2]+=row['minimum_L1_um']>500
 overruns=[];portgroups=defaultdict(lambda:{'bits':0,'worst_um':0,'max_extra_edges_if_500um_hops':0})
 for r in rows:
  if r['minimum_L1_um']<=500:continue
  source,sink=r['source'],r['sink'];key=source[0]+'.'+source[1].split('[')[0]+' -> '+sink[0]+'.'+sink[1].split('[')[0]
  extra=math.ceil(r['minimum_L1_um']/500)-1;g=portgroups[key];g['bits']+=1;g['worst_um']=max(g['worst_um'],r['minimum_L1_um']);g['max_extra_edges_if_500um_hops']=max(g['max_extra_edges_if_500um_hops'],extra)
  overruns.append({**r,'source_pin_shapes_um':coords(source,boxes),'sink_pin_shapes_um':coords(sink,boxes),'extra_registered_edges_lower_bound_if_positions_fixed':extra})
 overruns_by_variant[tag]={'net_port_groups':[{'net_port_pair':k,**v}for k,v in sorted(portgroups.items(),key=lambda item:(-item[1]['bits'],-item[1]['worst_um']))],'perbit_pin_legs':overruns,'stage_cost_warning':'Geometric hop lowerbound only. Actual static calendar and matched payload/control/valid paths must be implemented and full-RTL proven before any edge count is adopted.'}
 vm=[]
 for ep in boundary:
  if ep[0].startswith('shell.col') and ep[1].startswith('rs_d['):vm.append(outline[0]-max(x for x,y in coords(ep,boxes)))
 cuts={}
 for axis,axisindex in [('x',0),('y',1)]:
  candidates=sorted({round(b[axis]+b['w'if axis=='x'else'h']+10.8,3) for b in boxes.values() if b[axis]+b['w'if axis=='x'else'h']+10.8<outline[axisindex]})
  cutrows=[]
  for value in candidates:
   count=0;unique_drivers=set()
   for source,sink in joins:
    aa=[v[axisindex]for v in coords(source,boxes)];bb=[v[axisindex]for v in coords(sink,boxes)]
    if max(aa)<value<min(bb) or max(bb)<value<min(aa):
     count+=1;unique_drivers.add(source)
   cutrows.append({'position_um':value,'mandatory_crossing_bit_joins':count,'mandatory_crossing_unique_driver_bits':len(unique_drivers)})
  cuts[axis]=sorted(cutrows,key=lambda r:r['mandatory_crossing_bit_joins'],reverse=True)
 results[tag]={'mandatory_cut_inventory':cuts,'outline_um':outline,'overlap':0,'minimum_rect_L1_clearance_um':min(clearances),'incident_child_bit_joins':len(rows),'missing_LEF_terminals':0,'minimum_manhattan_sum_bit_um':sum(lengths),'minimum_manhattan_worst_um':max(lengths),'over500um_even_before_obstructions':sum(x>500for x in lengths),'p95_um':lengths[int(.95*len(lengths))],'VM_E_face_to_shell_return_minimum_max_um':max(vm),'VM_E_face_to_shell_return_minimum_mean_um':sum(vm)/len(vm),'largest_pairs':sorted([{'pair':k,'bits':v[0],'max_L1_um':v[1],'over500':v[2]}for k,v in groups.items()],key=lambda r:r['max_L1_um'],reverse=True)[:20],'placement':boxes}
print(json.dumps({k:{x:v for x,v in r.items()if x not in ('placement','largest_pairs','mandatory_cut_inventory')}for k,r in results.items()},indent=1))
receipt={'status':'ACTUAL_CONNECTED_GEOMETRY_SCREEN_ONLY','graph':'Yosys elaborated source38blackboxphysicalchildren; blackboxes use actual RTL headers, every data/control interchild terminal matched to actual routed LEF pin rectangles','leaf_views':hashes,'excluded_clock_reset_bits':dict(excluded),'perbit_joins':len(joins),'boundary_input_bits':len(boundary),'results':results,'limits':['Minimum L1 over all LEF terminal rectangle centers is optimistic, not routed RC or TT/FF proof','Clock/reset connections enumerated separately, no clocktree/reset PG plan qualified','Boundary VM span/lane per-bit y grants absent: Eface reach is only optimistic horizontal lowerbound','No timing waiver for over500um joins; added pipeline requires actual RTL/calendar proof','All R0 outlines; no90degree rotations or inherited rotated physical views','N inherited chunk ordering is concretized from prior geometry reservation, not a routed parent','Cut counts are mandatory endpoint-separated bit joins; no channel/layer track grant exists so no cut-capacity PASS claimed']}
(O/'over500_pin_legs.json').write_text(json.dumps(overruns_by_variant,indent=1)+'\n')
(O/'connected_geometry.json').write_text(json.dumps(receipt,indent=1)+'\n')
fig,axs=plt.subplots(2,3,figsize=(20,13));axs=axs.ravel()
for ax,(tag,(boxes,outline))in zip(axs,variants.items()):
 for n,b in boxes.items():
  ax.add_patch(Rectangle((b['x'],b['y']),b['w'],b['h'],facecolor='#b2df8a'if n.startswith('shell.')else'#bdcce3',edgecolor='black',linewidth=.5));ax.text(b['x']+b['w']/2,b['y']+b['h']/2,n.replace('mix.','').replace('shell.','s.').replace('.leaf',''),ha='center',va='center',fontsize=5)
 ax.axvline(outline[0]+21.6,color='red',lw=2);ax.set_aspect('equal');ax.set_xlim(-10,1140);ax.set_ylim(-10,910);ax.set_title(tag+'\n'+str(outline)+'um; E red=VM',fontsize=10)
 r=results[tag];ax.set_xlabel(f'actual bitjoins{len(joins)}; >500um {r["over500um_even_before_obstructions"]}\nworst {r["minimum_manhattan_worst_um"]:.1f}um; shell VM max {r["VM_E_face_to_shell_return_minimum_max_um"]:.1f}um')
# comparison uses every subplot
# axs[-1].text(0,1,'38 actual RTL children;10,396 bitjoins\nAll data/control pins match routed LEFs.\nMinimum L1 over terminal shapes only.\nNo native timing/cut/PG qualification.\nQuarter grouping improves all-incident wire cost;\nremaining long nets require source/calendar fix.\nAll outlines R0;21.6um minimum clearance.\nClock/reset reported separately,not qualified.',va='top',fontsize=14)
fig.suptitle('MIX4 source-connected R0 alternatives:optimistic actual LEF-pin L1; parent timing/cuts/PG OPEN');fig.tight_layout();fig.savefig(O/'connected_geometry.png',dpi=160)
