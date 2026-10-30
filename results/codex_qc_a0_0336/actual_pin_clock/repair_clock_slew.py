"""Plan-only structural repeater sizing from pure geometry/NLDM slew.
No routed timing, useful skew target, terminal padding, or RTL changes.
"""
import sys,json,math
from pathlib import Path
p=Path.cwd();sys.path.insert(0,str(p/'src'))
import gen_a0_clock_corridor as G
from gen_a0_regional_exact import ExactCorridor
source,model,kit,freeze,out=sys.argv[1:];sl=json.load(open(source));t=sl['core_tree'];m=json.load(open(model));fr=json.load(open(freeze));kd=Path(kit)
G.CLOCK_ISLANDS[:]=[r for c in fr['candidate_clock_corridors']for r in c['clock_islands_um']];G.CLOCK_COLUMNS[:]=[c['clock_reserved_rect_um']for c in fr['candidate_clock_corridors']];geo={};boxes=[]
for h in fr['hard_children']:
 if h['master']not in geo:geo[h['master']]=G.lef_geom(kd/'macros'/f"{h['master']}.lef")
 w,hh,_=geo[h['master']];x,y=h['at'];boxes.append((x-G.HALO[0],y-G.HALO[1],x+w+G.HALO[0],y+hh+G.HALO[1]))
P=ExactCorridor(boxes,100.);bad={r['driver']for c in m['corners'].values()for r in c['nets']if r['output_slew_max_ps']>60}
upsized=[]
for n in t['nodes']:
 if n['name']in bad and n['master']=='BUFx12f_ASAP7_75t_R':n['master']='BUFx24_ASAP7_75t_R';upsized.append(n['name'])
allnodes={n['name']:n for n in t['nodes']};allnodes.update({g['inst']:g for g in t['gates']});added=[];changes=[];serial=0
for name,n in list(allnodes.items()):
 parent=n['parent']
 if parent.startswith('port:'):continue
 a=allnodes[parent]['xy_um'];b=n['xy_um'];direct=G.man(a,b)
 if direct<=105:continue
 aa=P.legal(a);bb=P.legal(b);path=P.corridor(aa,bb)
 if G.man(a,path[0])>1e-6:path=[a]+path
 if G.man(path[-1],b)>1e-6:path=path+[b]
 length=sum(G.man(x,y)for x,y in zip(path,path[1:]));count=max(1,math.ceil(length/85)-1);par=parent;positions=[]
 for k in range(count):
  serial+=1;pos=P.along(path,length*(k+1)/(count+1));old=P.cell_width;P.cell_width=1.62
  try:pos=P.legal(pos)
  finally:P.cell_width=old
  row=dict(name=f'mp_slew_branch_{serial}',parent=par,master='BUFx24_ASAP7_75t_R',xy_um=pos);added.append(row);positions.append(pos);par=row['name']
 n['parent']=par;changes.append(dict(parent=parent,child=name,direct_um=direct,path_um=length,inserted=count))
t['nodes']+=added;parents={n['name']:n['parent']for n in t['nodes']};parents.update({g['inst']:g['parent']for g in t['gates']});depth={'port:ck':0}
def dep(n):
 if n not in depth:depth[n]=dep(parents[n])+1
 return depth[n]
for n in parents:dep(n)
t['nodes'].sort(key=lambda n:(dep(n['name']),n['name']));t.pop('model_qualification',None)
for l in t['leaves']:l.pop('pin_latency_ps',None)
Path(out+'.json').write_text(json.dumps(sl,indent=1)+'\n');report=dict(scope='MODEL ONLY structural slew repair; fresh NLDM prediction and fork balancing required',measured_timing_used=False,upsized=len(upsized),inserted_repeaters=serial,clock_nodes=len(t['nodes']),upsized_nodes=upsized,split_edges=changes,rtl_cycles_added=0);Path(out+'_repair.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({k:v for k,v in report.items()if k not in ['upsized_nodes','split_edges']}))
