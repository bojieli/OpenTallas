import odb,json,collections
from pathlib import Path
base=Path('/case/routes/gate/work/orfs/results/asap7/opentallas_qkd_hr_cdc_pc_sram_asap7_ref_gate/base')
for fn in ['3_4_place_resized.odb','3_5_place_dp-failed.odb']:
 db=odb.dbDatabase.create();odb.read_db(db,str(base/fn));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron();groups=collections.Counter();c=collections.Counter();samples=[];gridbad=[];rows=collections.defaultdict(list);placed=collections.defaultdict(list)
 for row in b.getRows():
  rx,ry=row.getOrigin();rows[ry].append((rx,row.getSpacing(),row.getSiteCount(),row.getSite().getWidth(),row.getSite().getHeight()))
 anchors=set()
 for af in ['ot_out_flop_at_pins.txt','ot_inhold_firm.txt']:
  anchors.update((base/af).read_text().splitlines())
 for i in b.getInsts():
  if i.getMaster().isBlock():continue
  bb=i.getBBox();x=(bb.xMin()+bb.xMax())/2/u;y=(bb.yMin()+bb.yMax())/2/u
  rowmatches=rows.get(bb.yMin(),[]);aligned=any(rx<=bb.xMin() and bb.xMax()<=rx+sp*(nc-1)+sw and (bb.xMin()-rx)%sp==0 for rx,sp,nc,sw,sh in rowmatches)
  if i.getName() in anchors:
   c['actual_anchor_count']+=1
   if not aligned:c['actual_anchor_grid_bad']+=1
   if i.getPlacementStatus() not in ['FIRM','LOCKED']:c['actual_anchor_not_fixed']+=1
   if bb.xMax()/u<=27:c['anchor_W_corridor']+=1
   elif bb.xMin()/u>=448.2:c['anchor_E_corridor']+=1
   elif bb.yMin()/u>=513:c['anchor_N_corridor']+=1
   else:c['anchor_outside_proposed_corridors']+=1
  cls='boundary' if i.getName().startswith(('ot_inhold_','ot_ihdrv_','ot_outhold_','ot_')) else ('central' if i.getGroup() else 'other')
  if not aligned:
   c['grid_bad_'+cls]+=1
   if cls=='boundary':print('BOUNDARY_OFFGRID',fn,i.getName(),bb.xMin(),bb.yMin())
   if len(gridbad)<12:gridbad.append([i.getName(),bb.xMin(),bb.yMin(),rowmatches[:2]])
  placed[bb.yMin()].append((bb.xMin(),bb.xMax(),i.getName(),cls))
  g=i.getGroup();gn=g.getName() if g else 'NONE';groups[gn]+=1
  if g:
   boxes=g.getRegion().getBoundaries()
   contained=any(z.xMin()<=bb.xMin() and z.xMax()>=bb.xMax() and z.yMin()<=bb.yMin() and z.yMax()>=bb.yMax() for z in boxes)
   if sum(z.xMin()<=bb.xMin() and z.xMax()>=bb.xMax() and z.yMin()<=bb.yMin() and z.yMax()>=bb.yMax() for z in boxes)>1:
    c['group_bbox_multiple_boxes']+=1
    if c['group_bbox_multiple_boxes']<=3:print('MULTI_BOX',fn,i.getName(),[bb.xMin(),bb.yMin()])
   if not contained:
    c['group_bbox_outside']+=1
    if c['group_bbox_outside']<=8:print('GROUP_OUT',fn,i.getName(),[bb.xMin(),bb.yMin(),bb.xMax(),bb.yMax()],[[z.xMin(),z.yMin(),z.xMax(),z.yMax()] for z in boxes])
  if 216<=y<=334.8:
   c['in_old_band']+=1
   if not g:
    c['ungrouped_in_old_band']+=1
    if x<27 or x>448.2:c['ungrouped_in_new_pin_corridor']+=1
    if len(samples)<12:samples.append([i.getName(),round(x,4),round(y,4),str(i.getPlacementStatus())])
  if i.getName().startswith(('ot_inhold_','ot_ihdrv_','ot_outhold_')):c['boundary_hold']+=1
 for ry,arr in placed.items():
  arr.sort();right=-1;prev=None
  for x0,x1,nm,cl in arr:
   if x0<right:c['overlap_'+cl+'_'+prev]+=1
   if x1>right:right=x1;prev=cl
 print(json.dumps(dict(file=fn,groups=groups,counts=c,ungrouped_samples=samples,grid_bad_samples=gridbad,row_samples=list(rows.items())[:3])))
