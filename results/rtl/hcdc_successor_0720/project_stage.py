import json,gzip,re,collections,odb,hashlib
from pathlib import Path
root=Path('/audit');j=json.load(gzip.open(root/'stage_identity.json.gz','rt'))
actual_path=Path('/case/routes/gate/work/orfs/results/asap7/opentallas_qkd_hr_cdc_pc_sram_asap7_ref_gate/base/3_5_place_dp-failed.odb')
adb=odb.dbDatabase.create();odb.read_db(adb,str(actual_path));actual=adb.getChip().getBlock()
pre=Path('/case/routes/gate/work/orfs/results/asap7/opentallas_qkd_hr_cdc_pc_sram_asap7_ref_gate/base/3_4_place_resized.odb')
db=odb.dbDatabase.create();odb.read_db(db,str(pre));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
ports={x['pin']:x for x in j['port_bits']};seq={x['instance']:x for x in j['sequential_instances']};ranges=json.load(open('/case/src/physical/ref_tile/qkd_hr_cdc_pc_sram1j/spec.json'))['pin_ranges']
for swap in [False]:
 moved={};unresolved=[];pnew={};inner={}
 for name,port in ports.items():
  x,y=port['xy_um'];base=port['base_port'];old=ranges[base]
  if port['actual_nearest_face'] not in ['W','E']:pnew[name]=[x,y];continue
  if base in ['ck_core','ck_phy_fam']:ran=[273,277]
  elif base in ['u_rank__physical_tx_d','u_rank__d_cd']:ran=[277,390]
  elif base in ['u_rank__raw_rx_d','u_rank__u_phy__pad_d']:ran=[160,273]
  else:ran=[160,390]
  if swap and base=='u_rank__physical_tx_d':ran=[160,273]
  if swap and base=='u_rank__raw_rx_d':ran=[277,390]
  yy=ran[0]+(y-old[0])/(old[1]-old[0])*(ran[1]-ran[0]);pnew[name]=[x,yy]
 for name,r in seq.items():
  member=set(r['direct_input_port_bits']+r['direct_output_port_bits'])
  if not member:
   if r['kind']=='synchronous_sram':continue
   ai=actual.findInst(name);bb=ai.getBBox();cx=(bb.xMin()+bb.xMax())/2/u;cy=(bb.yMin()+bb.yMax())/2/u
   tx=min(447.2,max(28.0,cx));ty=min(333.8,max(217.0,cy))
   clean=name.replace(chr(92),'');mm=re.search(r'(wq_data|od_q|bypass_data|id_q|o_d)\[(\d+)\]',clean)
   if mm and ('u_phy__u_rx.' in clean or 'u_phy__u_tx.' in clean):
    kind,bit=mm[1],int(mm[2]);istx='u_phy__u_tx.' in clean;core=(not istx if kind in ['od_q','o_d'] else istx)
    expected='port:ck_core' if core else 'port:ck_phy_fam';actual_clocks={src['name'] for cp in r['clock_pins'] for src in cp['sources']}
    if actual_clocks!={expected}:raise RuntimeError('SOURCE_ROLE_CLOCK_MISMATCH '+name+' '+str(actual_clocks))
    slot={'bypass_data':0,'wq_data':1 if '.g_mm.' in clean else 2,'od_q':3,'id_q':4,'o_d':5}[kind]
    tx=(270.0 if core else 145.8)+3.24*(bit%17);ty=225.18+2.16*(bit//17)+.27*slot
   inner[name]=(tx-cx,ty-cy)
   continue
  if len(member)!=1:unresolved.append([name,sorted(member)]);continue
  port=next(iter(member));pi=ports[port];i=b.findInst(name)
  if not i:raise RuntimeError('missing retained preplacement instance '+name)
  bb=i.getBBox();oldy=bb.yMin()/u;shift=pnew[port][1]-pi['xy_um'][1];target_y=round((oldy+shift-2.16)/.27)*.27+2.16
  moved[name]=dict(instance=i,dy=target_y-oldy,port=port)
 def xy(d):
  if d['kind'] in ['input_port','output_port','clock_source_port']:return pnew[d['pin']]
  if d.get('instance') in moved:
   v=moved[d['instance']];t=v['instance'].findITerm(d['pin']);ok,x,y=t.getAvgXY()
   if not ok:raise RuntimeError('missing preplacement pin')
   return [x/u,y/u+v['dy']]
  if d.get('instance') in inner:
   dx,dy=inner[d['instance']];return [d['xy_um'][0]+dx,d['xy_um'][1]+dy]
  return d['xy_um']
 roles=collections.Counter();over=[];maximum=0
 for e in j['data_stage_edges']:
  a,c=e['root'],e['endpoint'];aa=xy(a);cc=xy(c);dist=abs(aa[0]-cc[0])+abs(aa[1]-cc[1]);maximum=max(maximum,dist)
  if dist>405:over.append(dict(root=a['name'],endpoint=c['name'],L1=dist,root_xy=aa,end_xy=cc,role=a['kind']+'->'+c['kind']));roles[a['kind']+'->'+c['kind']]+=1
 over.sort(key=lambda z:-z['L1']);clocks=collections.Counter();cm={}
 for r in seq.values():
  for t in r['clock_pins']:
   for src in t['sources']:
    aa=xy(src);cc=xy(t);d=abs(aa[0]-cc[0])+abs(aa[1]-cc[1]);clocks[src['name']]+=1;cm[src['name']]=max(cm.get(src['name'],0),d)
 bins=collections.Counter();binarea=collections.Counter();targets={}
 for name,delta in inner.items():
  ai=actual.findInst(name);bb=ai.getBBox();cx=(bb.xMin()+bb.xMax())/2/u+delta[0];cy=(bb.yMin()+bb.yMax())/2/u+delta[1]
  key=(int((cx-2.16)//4.32),int((cy-2.16)//4.32));bins[str(key)]+=1;binarea[str(key)]+=ai.getMaster().getWidth()*ai.getMaster().getHeight()/u/u;targets[name]=[cx,cy]
 (root/'endpoint_targets.json').write_text(json.dumps(dict(interior_FF_targets=targets,bin_size_um=[4.32,4.32],bin_counts=bins,FF_only_bin_area_um2=binarea,NOT_legal_placement=True))+'\n')
 target_boxes={}
 for name,delta in inner.items():
  ai=actual.findInst(name);bb=ai.getBBox();cx=(bb.xMin()+bb.xMax())/2/u+delta[0];cy=(bb.yMin()+bb.yMax())/2/u+delta[1]
  x0=2.16+4.32*int((cx-2.16)//4.32);y0=2.16+4.32*int((cy-2.16)//4.32);target_boxes[name]=[x0,y0,x0+4.32,y0+4.32]
 for name,v in moved.items():
  bb=v['instance'].getBBox();cx=(bb.xMin()+bb.xMax())/2/u;cy=(bb.yMin()+bb.yMax())/2/u+v['dy']
  x0=2.16+4.32*int((cx-2.16)//4.32);y0=2.16+4.32*int((cy-2.16)//4.32);target_boxes[name]=[x0,y0,x0+4.32,y0+4.32]
 def endpoint_box(d):
  if d.get('instance') in target_boxes:return target_boxes[d['instance']]
  x,y=xy(d);return [x,y,x,y]
 boundmax=0;boundfails=[]
 for e in j['data_stage_edges']:
  aa=endpoint_box(e['root']);cc=endpoint_box(e['endpoint']);dd=max(abs(aa[0]-cc[2]),abs(aa[2]-cc[0]))+max(abs(aa[1]-cc[3]),abs(aa[3]-cc[1]));boundmax=max(boundmax,dd)
  if dd>405:boundfails.append([e['root']['name'],e['endpoint']['name'],dd])
 (root/'endpoint_target_boxes.json').write_text(json.dumps(dict(boxes=target_boxes,scope='conditional only if source-pinned ownership hook enforces complete cell bbox inside each target; constants/macros fixed baseline; no present physical admission'))+'\n')
 result=dict(scope='Constructive coordinate projection only: exact FULL Liberty-arc stage pairs; restore registered pin-stage membership to pre-DPL anchors, project y to230um ranges, interior FF centres clamped to proposed horizontal band (constructive targets only, not legal/overlap proof). Not legal P&R/candidate admission; source branch geometry must implement targets.',swap_core_data_halves=swap,pairs=len(j['data_stage_edges']),stage_over405=len(over),stage_max_L1=maximum,over_by_role=roles,worst=over[:40],moved_boundaryFF=len(moved),ambiguous_boundary_membership=unresolved,clock_sinks=clocks,clock_max_L1=cm,conditional_all_stage_box_max_L1=boundmax,conditional_stage_box_over405=len(boundfails),conditional_stage_box_worst=sorted(boundfails,key=lambda z:-z[2])[:3],max_FF_bin_density=max(binarea.values(),default=0)/(4.32*4.32))
 (root/('projection_swap.json' if swap else 'projection_role_boxes.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['worst','ambiguous_boundary_membership']}));print('worst',over[:5])
