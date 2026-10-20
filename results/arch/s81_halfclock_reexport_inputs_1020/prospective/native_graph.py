import odb,json,hashlib,os,re,collections
from pathlib import Path
B=Path('/stage');rows=json.loads((B/'cases.json').read_text());roles=json.loads((B/'current_image_native_sources.json').read_text())['cell_roles'];out=[]
for row in rows:
 m=row['master'];p=next(f['path'] for f in row['files'] if f['path'].endswith('6_final.odb'));db=odb.dbDatabase.create();odb.read_db(db,p);block=db.getChip().getBlock();u=block.getDbUnitsPerMicron();insts=[];missing=[];masters={};netdata={};bterms=[];signalroleerrors=[]
 for inst in block.getInsts():
  master=inst.getMaster();mn=master.getName();role=roles.get(mn)
  if role is None:signalroleerrors.append(dict(inst=inst.getName(),master=mn,error='missing_loaded_Liberty_role'))
  masters[mn]=dict(width_um=master.getWidth()/u,height_um=master.getHeight()/u,mterms=[dict(name=t.getName(),io=str(t.getIoType()),sig=str(t.getSigType())) for t in master.getMTerms()],Liberty=role)
  ts=[]
  for t in inst.getITerms():
   pin=t.getMTerm().getName();net=t.getNet();n=net.getName() if net else None;sig=str(t.getSigType());ok,x,y=t.getAvgXY();r=dict(pin=pin,net=n,io=str(t.getIoType()),sig=sig,xy_um=[x/u,y/u] if ok else None)
   ts.append(r)
   if sig in ['POWER','GROUND'] and (net is None or str(net.getSigType()) not in ['POWER','GROUND']):missing.append(dict(instance=inst.getName(),master=mn,**r))
   if n is not None and sig not in ['POWER','GROUND']:netdata.setdefault(n,dict(terms=[],bterms=[]))['terms'].append(dict(instance=inst.getName(),master=mn,**r))
  insts.append(dict(name=inst.getName(),master=mn,status=str(inst.getPlacementStatus()),dont_touch=inst.isDoNotTouch(),terms=ts))
 for bt in block.getBTerms():
  net=bt.getNet();n=net.getName() if net else None;bs=[]
  for bp in bt.getBPins():
   for bx in bp.getBoxes():bs.append(dict(layer=bx.getTechLayer().getName(),bbox_um=[bx.xMin()/u,bx.yMin()/u,bx.xMax()/u,bx.yMax()/u]))
  r=dict(name=bt.getName(),net=n,io=str(bt.getIoType()),sig=str(bt.getSigType()),boxes=bs);bterms.append(r)
  if n in netdata:netdata[n]['bterms'].append(r)
 im={i['name']:i for i in insts}
 def unary(master):
  r=roles[master];ins=[p for p,d in r['pins'].items() if d['direction']=='input'];outs=[p for p,d in r['pins'].items() if d['direction']=='output']
  if r['sequential'] or len(ins)!=1 or len(outs)!=1:return None
  f=(r['pins'][outs[0]]['function'] or '').replace(' ','').replace('(','').replace(')','')
  if f==ins[0]:return (ins[0],outs[0],0)
  if f in ['!'+ins[0],'~'+ins[0],ins[0]+"'"]:return (ins[0],outs[0],1)
  return None
 def trace(net):
  seen=set();path=[];parity=0
  while True:
   if net in seen:return dict(error='clock_loop',path=path)
   seen.add(net);n=netdata.get(net,{});sources=[b for b in n.get('bterms',[]) if b['io']=='INPUT'];drivers=[t for t in n.get('terms',[]) if t['io']=='OUTPUT']
   if sources:
    return dict(root=sources[0]['name'],root_count=len(sources),driver_count=len(drivers),parity=parity,path=path)
   if len(drivers)!=1:return dict(error='nonunique_driver',net=net,path=path,drivers=len(drivers))
   t=drivers[0];typ=unary(t['master'])
   if typ is None:return dict(error='nonunary_native_clock_driver',driver=t,path=path)
   inp,op,inv=typ;parity^=inv;path.append(dict(instance=t['instance'],master=t['master'],output=t['pin'],function=roles[t['master']]['pins'][op]['function'],inverted=inv));net=next(z['net'] for z in im[t['instance']]['terms'] if z['pin']==inp)
 clocks=[]
 for i in insts:
  for t in i['terms']:
   if roles.get(i['master'],{}).get('pins',{}).get(t['pin'],{}).get('clock'):clocks.append(dict(instance=i['name'],master=i['master'],pin=t['pin'],trace=trace(t['net'])))
 ob=next(x for x in bterms if x['name']=='ck_o');forward=trace(ob['net']);reach=[]
 for name,n in netdata.items():
  pts=[t['xy_um'] for t in n['terms'] if t['xy_um']]
  for bt in n['bterms']:
   pts.extend([[(z['bbox_um'][0]+z['bbox_um'][2])/2,(z['bbox_um'][1]+z['bbox_um'][3])/2] for z in bt['boxes']])
  if len(pts)<2:continue
  d=max(max(x+y for x,y in pts)-min(x+y for x,y in pts),max(x-y for x,y in pts)-min(x-y for x,y in pts))
  if d>405:reach.append(dict(net=name,direct_manhattan_um=d))
 cerrors=[c for c in clocks if c['trace'].get('error') or c['trace'].get('root')!='ck' or c['trace'].get('root_count')!=1 or c['trace'].get('driver_count')!=0]
 pgnets=[dict(name=n.getName(),sig=str(n.getSigType()),swires=len(n.getSWires())) for n in block.getNets() if str(n.getSigType()) in ['POWER','GROUND']]
 status='PREFLIGHT_PASS_ONLY' if clocks and len(pgnets)>=2 and all(z['swires']>0 for z in pgnets) and not missing and not signalroleerrors and not cerrors and not reach and forward.get('root')=='ck' and forward.get('parity')==1 else 'REFUSED_NO_EXPORT'
 r=dict(master=m,status=status,odb_sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest(),nativePG_unbound=missing,PG_nets=pgnets,Liberty_role_errors=signalroleerrors,native_clock_pins=clocks,native_clock_graph_errors=cerrors,forward_clock_chain=forward,direct_reach_over405=reach,reach_scope='directnet terminal maximum Manhattan only, not fullcomb-stage or detailedroute proof',masters=masters,instances=insts,bterms=bterms)
 (B/(m+'_native_preflight.json')).write_text(json.dumps(r,indent=2));out.append(dict(master=m,status=status,instances=len(insts),unboundPG=len(missing),roleerrors=len(signalroleerrors),clockpins=len(clocks),clockerrors=len(cerrors),over405=len(reach),forward_root=forward.get('root'),forward_parity=forward.get('parity')))
 print('NATIVE_PREFLIGHT',out[-1],flush=True)
(B/'native_preflight_summary.json').write_text(json.dumps(out,indent=2))
