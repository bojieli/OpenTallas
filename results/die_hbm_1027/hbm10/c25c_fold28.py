"""Place missing S-role q0 service instances near their original N-role template.
Usage SRC OUT REQUIREMENTS. These are existing native RTL producers, not added logical throughput.
Copies only real service leaves: never whole SU slices, and never whole scorer quarters whose children already exist.
"""
import copy,hashlib,json,math,shutil,sys
from pathlib import Path
from shapely.geometry import box
from shapely.strtree import STRtree
src,out,req=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=True)
for f in src.iterdir():
 if f.is_file() and f.suffix=='.json':shutil.copy2(f,out/f.name)
shutil.copytree(src/'cores',out/'cores',dirs_exist_ok=True)
p=json.loads((src/'die_plan.json').read_text());r=json.loads(req.read_text());report={'source_sha256':hashlib.sha256((src/'die_plan.json').read_bytes()).hexdigest(),'event':'C25c missing physical S-role service leaves','data_cycles_added':0,'instances':[],'mapping':{}}
for tn,part in [('q_hub_nw','NW_hub'),('q_hub_ne','NE_hub')]:
 t=p['partition_types'][tn];ob=[]
 for c in t.get('hard_cores',[])+t['contents']:
  if not c.get('origin_um') or not c.get('outline_um'):continue
  x,y=c['origin_um'];w,h=c['outline_um'];dx,dy=c.get('track_offset_um',[0,0]);ob.append(box(x+dx-4.32,y+dy-4.32,x+dx+w+4.32,y+dy+h+4.32))
 for ft in t['ft_slots']:
  cw,ch=ft.get('bit_site_cell_um',[1.404,.27])
  for stage in ft.get('bit_sites_um',[]):
   ob.extend(box(x-cw/2,y-ch/2,x+cw/2,y+ch/2) for x,y in stage)
 for s in t.get('internal_stations',[]):
  ob.extend(box(x-1.08,y-.27,x+1.08,y+.27) for x,y in s.get('regs_um',[]))
 tree=STRtree(ob);added=[]
 for row in [a for a in r['hub_candidates'] if a['partition']==part]:
  old=row['template_plan_inst'];orig=next(c for c in t['contents'] if c['inst']==old);hc=next((c for c in t['hard_cores'] if c['inst']==old),None)
  shape=hc or orig;x0,y0=shape['origin_um'];w,h=shape['outline_um'];name=old+'__q0'
  assert not any(c['inst']==name for c in t['contents'])
  found=None
  # Nearest lattice point with real core/soft lot/station clearance, <=~2.2mm scan.
  for radius in range(1,260):
   cand=[]
   for ix in range(-radius,radius+1):
    iy=radius-abs(ix)
    for yy in ({iy,-iy} if iy else {0}):cand.append((ix,yy))
   for ix,iy in cand:
    x=round(x0+ix*8.64,4);y=round(y0+iy*8.64,4)
    if x<4.32 or y<4.32 or x+w>t['outline_um'][0]-4.32 or y+h>t['outline_um'][1]-4.32:continue
    b=box(x-4.32,y-4.32,x+w+4.32,y+h+4.32)
    if len(tree.query(b,predicate='intersects')) or any(b.intersects(a) for a in added):continue
    found=(x,y,b);break
   if found:break
  assert found is not None,(tn,old,w,h)
  x,y,b=found;added.append(b);c=copy.deepcopy(orig);c.update(inst=name,origin_um=[x,y],outline_um=[w,h],note=f'C25c existing native S-role producer {row["asbuilt_required"]}; independent q0 copy, no queue sharing')
  if row['template_master']=='ot_hbm_host_cfg_leaf2':
   c['module']=row['template_master'];c['params']={'NT':20 if part=='NW_hub' else 21,'NF':32 if part=='NW_hub' else 31};c['note']+='; exact source NT/NF, no stale _nw/_ne alias'
  t['contents'].append(c)
  if hc:
   nh=copy.deepcopy(hc);nh.update(inst=name,origin_um=[x,y]);nh.pop('lef',None);nh.pop('lib',None);nh['note']=c['note'];t['hard_cores'].append(nh)
   oldt=[a for a in t['clock']['taps'] if a['name'].startswith(old+'.')]
   for tap in oldt:
    nt=copy.deepcopy(tap);nt['name']=name+tap['name'][len(old):];nt['xy']=[round(tap['xy'][0]+x-x0,4),round(tap['xy'][1]+y-y0,4)];t['clock']['taps'].append(nt)
  report['mapping'][row['asbuilt_required']]=[part,name]
  report['instances'].append({'type':tn,'instance':name,'module':c['module'],'outline_um':[w,h],'origin_um':[x,y],'template':old,'displacement_um':round(abs(x-x0)+abs(y-y0),4),'hard_core':bool(hc),'status':'PLACED; connectivity reach and region assignment pending current bind'})
# The placement alone is not a routed-plan or token-pass claim.
report['added_lot_area_mm2']=sum(a['outline_um'][0]*a['outline_um'][1]/1e6 for a in report['instances']);report['new_instances']=len(report['instances']);assert report['new_instances']==28
p['note']=p.get('note','')+' | C25c missing28S-role service producers placed, no SU/scorer duplication; connectivity/station integration pending'
(out/'die_plan.json').write_text(json.dumps(p,indent=1));report['plan_sha256']=hashlib.sha256((out/'die_plan.json').read_bytes()).hexdigest();(out/'c25c_fold28_report.json').write_text(json.dumps(report,indent=1));print(json.dumps(report,indent=1)[:3000])
