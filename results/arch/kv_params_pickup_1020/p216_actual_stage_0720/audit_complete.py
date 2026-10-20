import odb,json,pathlib,hashlib,sys,collections,heapq
sys.path.insert(0,'/src/tools/ref_tile')
import native_census as NC
print('AUDIT_START',flush=True)
r=pathlib.Path('/audit'); work=pathlib.Path('/work'); native=json.loads((work/'native_census.json').read_text());roles,libreceipt=NC.liberty_roles([x['path'] for x in native['liberty']]);assert {x['sha256'] for x in libreceipt}=={x['sha256'] for x in native['liberty']}
print('LIB_ROLES_READY',len(roles),flush=True)
base=work/'results/asap7/opentallas_ot_qwen_tp8_pv_join_s32_t_asap7_ref_gate/base'
for stage in ['4_cts','5_1_grt']:
 print('READ_STAGE',stage,flush=True)
 path=base/(stage+'.odb'); db=odb.dbDatabase.create();odb.read_db(db,str(path));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron(); errors=[];pins={};seq=set();transparent=set();insts={};pg=collections.Counter();pg_open=[];netrows=[];edges=collections.defaultdict(list);indeg=collections.Counter();boundary=[];components=collections.defaultdict(list)
 for inst in b.getInsts():
  name=inst.getName(); master=inst.getMaster().getName();role=roles.get(master);insts[name]=master
  if role is None:
   physical_pins=list(inst.getITerms())
   if physical_pins and all(str(t.getSigType()) in ('POWER','GROUND') for t in physical_pins):
    role={'sequential':False,'pins':{}};pg['physical_pg_only_instances']+=1
   else:errors.append('missing_lib_master:'+master);continue
  if role['sequential']:seq.add(name)
  ins=[p for p,z in role['pins'].items() if z['direction']=='input'];outs=[p for p,z in role['pins'].items() if z['direction']=='output']
  if not role['sequential'] and len(ins)==len(outs)==1 and role['pins'][outs[0]]['function'] in (ins[0],'!'+ins[0],'('+ins[0]+')'):transparent.add(name)
  for t in inst.getITerms():
   pn=t.getMTerm().getName(); key=name+'/'+pn; ok,x,y=t.getAvgXY(); box=inst.getBBox()
   if not ok:errors.append('missing_pin_geometry:'+key);x=(box.xMin()+box.xMax())/2;y=(box.yMin()+box.yMax())/2
   pr=role['pins'].get(pn)
   if str(t.getSigType()) in ('POWER','GROUND'):
    kind=str(t.getSigType());pg[kind+'_iterms']+=1;net=t.getNet()
    if net is None or len(net.getName())==0 or str(net.getSigType())!=kind:
     pg_open.append({'inst':name,'pin':pn,'master':master,'role':kind,'net':net.getName() if net else None,'net_sigtype':str(net.getSigType()) if net else None,'placement_status':str(inst.getPlacementStatus()),'protected':bool(inst.isDoNotTouch()) if hasattr(inst,'isDoNotTouch') else None})
   elif pr is None:kind='UNRESOLVED';errors.append('missing_lib_pin:'+key)
   elif pr['clock']:kind='LIB_CLOCK'
   elif role['sequential']:kind='SEQ_'+pr['direction'].upper()
   elif pr['direction']=='output' and str(pr.get('function')).strip('() ') in ('0','1'):kind='CONSTANT_OUTPUT'
   else:kind='COMB_'+pr['direction'].upper()
   pins[key]={'inst':name,'pin':pn,'master':master,'role':kind,'xy':[x/u,y/u],'direction':str(t.getIoType()),'net':t.getNet().getName() if t.getNet() else None}
 for t in b.getBTerms():
  key='@PORT/'+t.getName();boxes=[z for pp in t.getBPins() for z in pp.getBoxes()]
  if not boxes:errors.append('missing_port_geometry:'+key);xy=None
  else:xy=[sum((z.xMin()+z.xMax())/2 for z in boxes)/len(boxes)/u,sum((z.yMin()+z.yMax())/2 for z in boxes)/len(boxes)/u]
  pins[key]={'inst':'@PORT','pin':t.getName(),'role':'TOP_'+str(t.getSigType())+'_'+str(t.getIoType()),'xy':xy,'direction':str(t.getIoType()),'net':t.getNet().getName() if t.getNet() else None}
 print('PINS_READY',stage,len(pins),flush=True)
 for net in b.getNets():
  sig=str(net.getSigType()); name=net.getName(); keys=[t.getInst().getName()+'/'+t.getMTerm().getName() for t in net.getITerms()]+['@PORT/'+t.getName() for t in net.getBTerms()];keys=[k for k in keys if k in pins]
  if sig in ('POWER','GROUND'):
   pg[sig+'_nets']+=1;pg[sig+'_connected_pins']+=len(keys);continue
  drivers=[k for k in keys if (pins[k]['inst']=='@PORT')==(pins[k]['direction']=='INPUT')];loads=[k for k in keys if k not in drivers]
  if len(drivers)!=1:
   errors.append('driver_count:'+name+':'+str(len(drivers)));continue
  dr=drivers[0]; a=pins[dr]
  for ld in loads:
   z=pins[ld]
   if a['xy'] is None or z['xy'] is None:continue
   reach=sum(abs(a['xy'][i]-z['xy'][i]) for i in (0,1)); rec={'net':name,'driver':dr,'load':ld,'driver_role':a['role'],'load_role':z['role'],'manhattan_um':reach};netrows.append(rec)
   src='ROOT:'+dr if a['inst']=='@PORT' or a['inst'] in seq or a['role']=='CONSTANT_OUTPUT' else a['inst'];dst='END:'+ld if z['inst']=='@PORT' or z['inst'] in seq else z['inst'];edges[src].append((dst,reach,name,dr,ld));indeg[src]+=0;indeg[dst]+=1
 print('NETS_READY',stage,len(netrows),flush=True)
 # Full combinational path sum, includes actual Liberty-clock endpoints. No clock/data name exemption.
 q=collections.deque(k for k,v in indeg.items() if not v);best={k:(0,None) for k in q};done=0
 extreme={}
 def forms(xy):return [xy[0]+xy[1],xy[0]-xy[1],-xy[0]+xy[1],-xy[0]-xy[1]]
 for k in q:
  if k.startswith('ROOT:'):
   pin=k[5:];extreme[k]=[(v,pin) for v in forms(pins[pin]['xy'])]
 while q:
  k=q.popleft();done+=1
  for dst,reach,net,dr,ld in edges[k]:
   if k in extreme:
    if dst not in extreme:extreme[dst]=list(extreme[k])
    else:extreme[dst]=[max(a,b) for a,b in zip(extreme[dst],extreme[k])]
   val=best[k][0]+reach
   if dst not in best or val>best[dst][0]:best[dst]=(val,[k,net,dr,ld])
   indeg[dst]-=1
   if indeg[dst]==0:q.append(dst)
 endpoint_rows=[]
 for endpoint,ex in extreme.items():
  if endpoint.startswith('END:'):
   ld=endpoint[4:];target=forms(pins[ld]['xy']);distance,dr=max((v-target[i],root) for i,(v,root) in enumerate(ex));endpoint_rows.append({'driver':dr,'load':ld,'driver_role':pins[dr]['role'],'load_role':pins[ld]['role'],'manhattan_um':distance})
 worst=max(best,key=lambda k:best[k][0]);chain=[];cur=worst
 while best[cur][1] is not None:
  prev,net,dr,ld=best[cur][1];chain.append([net,dr,ld]);cur=prev
 instpins=collections.defaultdict(list)
 for kk,zz in pins.items():instpins[zz['inst']].append(kk)
 # Boundary tracing crosses only Liberty-proved transparent unary cells.
 def boundary_trace(start,forward):
  seen=set();todo=[start];ends=[]
  while todo:
   key=todo.pop()
   if key in seen:continue
   seen.add(key);pn=pins[key];net=pn['net']
   if net is None:ends.append([key,'UNCONNECTED']);continue
   nk=[t.getInst().getName()+'/'+t.getMTerm().getName() for t in b.findNet(net).getITerms()]+['@PORT/'+t.getName() for t in b.findNet(net).getBTerms()]
   for kk in nk:
    if kk==key or kk not in pins:continue
    zz=pins[kk];isdriver=(zz['inst']=='@PORT')==(zz['direction']=='INPUT')
    if isdriver==forward:continue
    if zz['inst'] in transparent:
     other=[k for k in instpins[zz['inst']] if pins[k]['direction']!=zz['direction'] and pins[k]['role'] not in ('POWER','GROUND')]
     todo.extend(other)
    else:ends.append([kk,zz['role']])
  return ends
 for k,z in pins.items():
  if z['inst']=='@PORT' and 'POWER' not in z['role'] and 'GROUND' not in z['role']:
   ends=boundary_trace(k,z['direction']=='INPUT');boundary.append({'port':z['pin'],'direction':z['direction'],'endpoints':ends})
 report={'stage':stage,'odb_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'liberty':libreceipt,'source_manifest_sha256':'acb28b78a3869a15bf650ccb61fc31afad7de8ff2f1448ad76bc64d88a525ad0','units':u,'die_um':[b.getDieArea().xMin()/u,b.getDieArea().yMin()/u,b.getDieArea().xMax()/u,b.getDieArea().yMax()/u],'errors':errors,'physical_pg_only_rule':'No Liberty cell only admitted when every actual ODB ITerm is POWER/GROUND; no SIGNAL/CLOCK pins, no name exemption','pg_open':pg_open,'pg_open_by_master':dict(collections.Counter(x['master'] for x in pg_open)),'pg_open_by_status':dict(collections.Counter(x['placement_status'] for x in pg_open)),'pin_roles':dict(collections.Counter(x['role'] for x in pins.values())),'pg':dict(pg),'all_direct_driver_load_pairs':len(netrows),'max_direct_pair':max(netrows,key=lambda x:x['manhattan_um']),'direct_pairs_over405':[x for x in netrows if x['manhattan_um']>405+1e-6],'max_registered_stage_endpoint_l1':max(endpoint_rows,key=lambda x:x['manhattan_um']),'registered_stage_endpoints_checked':len(endpoint_rows),'registered_stage_endpoints_over405':[x for x in endpoint_rows if x['manhattan_um']>405+1e-6],'stage_endpoint_method':'Four signed coordinate extrema propagated through the full conservative combinational cell graph from each actual sequential/port/constant driver to sequential or output-port boundary. All clock pins included; combinational cells do not stop the stage. Multi-output cell dependence conservatively overapproximated.','max_comb_stage_sum_manhattan_um':best[worst][0],'max_comb_stage_chain':list(reversed(chain)),'unresolved_comb_nodes':sum(v>0 for v in indeg.values()),'boundary':boundary,'limits':['Geometric direct pin L1 and conservative summed combinational wire displacement, not timing signoff or routed wirelength.','All clock endpoints included by actual Liberty roles. PG separately enumerated by ODB sigtype; no clock/data name exemption.']}
 (r/(stage+'_complete_audit.json')).write_text(json.dumps(report,indent=2));(r/(stage+'_pins.json')).write_text(json.dumps(pins));print(stage,json.dumps({'errors':len(errors),'max_direct_pair':report['max_direct_pair'],'max_registered_stage_endpoint_l1':report['max_registered_stage_endpoint_l1'],'endpoints_checked':len(endpoint_rows),'max_comb_stage_sum_manhattan_um':best[worst][0],'pg_open':len(pg_open),'pg_open_by_master':report['pg_open_by_master'],'pg':dict(pg)}),flush=True)
