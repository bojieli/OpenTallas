# Endpoint-only capacity proof. Other movable combinational cells are NOT placed.
import odb,json,gzip,math,collections
from pathlib import Path
out=Path('/audit');data=json.load(gzip.open(out/'stage_identity.json.gz','rt'));targets=json.load(open(out/'endpoint_target_boxes.json'))['boxes']
p=Path('/case/routes/gate/work/orfs/results/asap7/opentallas_qkd_hr_cdc_pc_sram_asap7_ref_gate/base/3_5_place_dp-failed.odb')
db=odb.dbDatabase.create();odb.read_db(db,str(p));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron();pitch=54;height=270;halo=10800
rows={}
for row in b.getRows():
 x,y=row.getOrigin();rows[y]=str(row.getOrient())
# Preserve every actual macro halo and fixed physical-only bbox as forbidden.
obstacles=[]
for i in b.getInsts():
 bb=i.getBBox();pad=halo if i.getMaster().isBlock() else 0
 sig=any(t.getSigType() not in ['POWER','GROUND'] for t in i.getITerms())
 if i.getMaster().isBlock() or (not sig and str(i.getPlacementStatus()) in ['LOCKED','FIRM','COVER']):obstacles.append((bb.xMin()-pad,bb.yMin()-pad,bb.xMax()+pad,bb.yMax()+pad))
# Constants also need explicit ownership; they are not allowed arbitrary later movement.
constants={c['instance'] for c in data['constant_function_sources']}
for name in constants:
 i=b.findInst(name);bb=i.getBBox();cx=(bb.xMin()+bb.xMax())/2/u;cy=(bb.yMin()+bb.yMax())/2/u;x0=2.16+4.32*int((cx-2.16)//4.32);y0=2.16+4.32*int((cy-2.16)//4.32);targets[name]=[x0,y0,x0+4.32,y0+4.32]
groups=collections.defaultdict(list);errors=[]
for name,box in targets.items():
 i=b.findInst(name)
 if not i:errors.append('missing source endpoint:'+name);continue
 m=i.getMaster()
 if m.getHeight()!=height or m.getWidth()%pitch:errors.append('unsupported endpoint grid geometry:'+name)
 groups[tuple(round(x*u) for x in box)].append(i)
placements={};failed=[];occupied_area=0;available_area=0
for box,insts in sorted(groups.items()):
 x0,y0,x1,y1=box;free=[]
 for y in range(y0,y1,height):
  if y not in rows:continue
  avail=[True]*int((x1-x0)//pitch)
  for a,c,d,e in obstacles:
   if y+height<=c or y>=e or x1<=a or x0>=d:continue
   lo=max(0,(a-x0)//pitch);hi=min(len(avail),math.ceil((d-x0)/pitch))
   for k in range(lo,hi):avail[k]=False
  free.append((y,avail));available_area+=sum(avail)*pitch*height/u/u
 for i in sorted(insts,key=lambda z:(-z.getMaster().getWidth(),z.getName())):
  width=i.getMaster().getWidth();n=width//pitch;chosen=None
  for y,avail in free:
   run=0
   for k,v in enumerate(avail):
    run=run+1 if v else 0
    if run>=n:chosen=(y,k-n+1,avail);break
   if chosen:break
  if not chosen:failed.append(dict(name=i.getName(),box=box,master=i.getMaster().getName(),width_dbu=width));continue
  y,k,avail=chosen
  for ix in range(k,k+n):avail[ix]=False
  x=x0+k*pitch;i.setOrient(rows[y]);i.setLocation(x,y)
  bb=i.getBBox()
  if not(x0<=bb.xMin() and bb.xMax()<=x1 and y0<=bb.yMin() and bb.yMax()<=y1):errors.append('packed cell outside target:'+i.getName())
  placements[i.getName()]=dict(x_dbu=x,y_dbu=y,orientation=rows[y],box_dbu=box);occupied_area+=width*height/u/u
# Re-evaluate ALL source-bound stage endpoints with actual packed ITerm geometry.
def xy(d):
 if d.get('instance') in placements:
  t=b.findInst(d['instance']).findITerm(d['pin']);ok,x,y=t.getAvgXY()
  if not ok:raise RuntimeError('missing packed pin geometry')
  return [x/u,y/u]
 if d['kind'] in ['input_port','output_port','clock_source_port']:
  # The constructive pin-span target is supplied by the same archived model.
  return d['xy_um']
 return d['xy_um']
maximum=0;over=[]
for edge in data['data_stage_edges']:
 a,c=edge['root'],edge['endpoint'];aa,cc=xy(a),xy(c);dd=abs(aa[0]-cc[0])+abs(aa[1]-cc[1]);maximum=max(maximum,dd)
 if dd>405:over.append([a['name'],c['name'],dd])
result=dict(scope='Endpoint-only row/site packing inside conditional target boxes, preserving actual macro halos and locked physical cells; all other movable combinational cells deliberately unplaced/unvalidated, NOT legal whole-design/P&R admission. Port coordinates in this check remain frozen baseline (new230um target pin positions are NOT deposited).',source_FF_targets=len(targets)-len(constants),source_constant_cells=len(constants),target_bins=len(groups),packed_endpoint_cells=len(placements),failed_cells=len(failed),errors=errors,failures=failed[:20],endpoint_area_um2=occupied_area,available_bin_area_um2=available_area,all_stage_pairs=len(data['data_stage_edges']),stage_over405=len(over),stage_max_L1=maximum,worst=sorted(over,key=lambda x:-x[2])[:10])
(out/'endpoint_pack.json').write_text(json.dumps(result,indent=2)+'\n');(out/'endpoint_pack_placements.json').write_text(json.dumps(placements)+'\n');print(json.dumps(result));
if failed or errors:raise SystemExit(2)
