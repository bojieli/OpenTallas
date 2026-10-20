import json,hashlib,collections,sys,re
from pathlib import Path
basis=Path('/home/ubuntu/artifacts/hdie-d4/d4g_gen2e/banklat/contract_gen2c_l12.json');c=json.loads(basis.read_text());I=c['instances'];E=c['edges'];outs=collections.defaultdict(list)
for e in E:outs[tuple(e['source'][:2])].append(e)
client='su_SW0';isrelay=lambda n: bool(re.match(r'^hbfd_(rly|pad|lh0?|lnd|land0?)[A-Za-z0-9_]*$',I[n]['master']))
def trace(i,p,b,goal):
 out=[];stack=[(i,p,b,[])];seen=set()
 while stack:
  ni,np,nb,h=stack.pop();key=(ni,np,nb)
  if key in seen:raise ValueError('cycle '+str(key))
  seen.add(key)
  for e in outs.get((ni,np),[]):
   si,sp,sl,sh=e['source'];ki,kp,kl,kh=e['sink']
   if not sl<=nb<sh:continue
   kb=kl+nb-sl
   if goal(ki,kp,kb):out.append(dict(endpoint=[ki,kp,kb],hops=h,edges=[]))
   elif isrelay(ki) and kp in ('i','a'):stack.append((ki,{'i':'o','a':'b'}[kp],kb,h+[ki]))
 return out
paths=[];nodes={client}
for q,r,kind,width,rwidth in [('lg_rq','lg_rr','read',17,257),('lg_wq','lg_w_done','write',281,1)]:
 for lane in range(2):
  qr=[]
  for bit in range(width):
   hit=trace(client,q,lane*width+bit,lambda i,p,b:I[i]['master'] in ('hfd_vms_bank_native_q0_faces','ot_vms_bank_static','hfd_vms_bank_native_q0'))
   assert len(hit)==1,(q,lane,bit,hit)
   if bit==0:request=hit[0]
   assert hit[0]['hops']==request['hops'] and hit[0]['endpoint'][:2]==request['endpoint'][:2] and hit[0]['endpoint'][2]==bit
  bk,bp,_=request['endpoint'];rp=({'rq0':'rr0','rq1':'rr1','rq2':'rr2','rq3':'rr3','rq4':'rr4','pq':'pr'} if kind=='read' else {'wq0':'wq_done0','wq1':'wq_done1','dq':'dq_done','kq':'kq_done','xq':'xq_done','xq2':'xq2_done'})[bp]
  for bit in range(rwidth):
   hit=trace(bk,rp,bit,lambda i,p,b:i==client and p==r)
   assert len(hit)==1,(r,lane,bit,hit)
   if bit==0:response=hit[0]
   assert hit[0]['hops']==response['hops'] and hit[0]['endpoint'][2]==lane*rwidth+bit
  paths.append(dict(kind=kind,lane=lane,request_port=q,return_port=r,request_bits=width,return_bits=rwidth,bank=bk,bank_request_port=bp,bank_return_port=rp,request_hops=request['hops'],return_hops=response['hops']))
  nodes.update([bk]+request['hops']+response['hops'])
# Lane edge accounting uses the production source-owned rules, without expanding the whole bit graph.
sys.path.insert(0,'/home/ubuntu/wt/codex-hd4g-strict-1019/tools/hbm_die_v16');import d4g_bank_latency as L
g=object.__new__(L.Graph);g.I=I
for p in paths:
 a,an=g.lane_latency(p['request_hops']);b,bn=g.lane_latency(p['return_hops']);pin=L.BANK_PIN[I[p['bank']]['master']];bank=L.BANK_RD if p['kind']=='read' else L.BANK_WR
 p.update(request_edges=a,return_edges=b,bank_internal_edges=bank,bank_face_edges=pin,source_port_roundtrip=a+b+bank+pin,local_su_edges=4,required_parameter=a+b+bank+pin+4,unresolved=an+bn)
 assert not p['unresolved'],p
 assert p['required_parameter']==(18 if p['kind']=='read' else 15),p
ins=collections.defaultdict(list)
for e in E:ins[tuple(e['sink'][:2])].append(e)
reset_paths=[]
for target in sorted(nodes):
 for cp,meta in I[target]['ports'].items():
  if not re.search(r'(rst|reset)',cp) or meta.get('direction')!='input':continue
  cur=(target,cp,0);chain=[];seen=set()
  while cur not in seen:
   seen.add(cur);ni,np,nb=cur;hit=[e for e in ins.get((ni,np),[]) if e['sink'][2]<=nb<e['sink'][3]]
   if not hit:break
   assert len(hit)==1,(cur,hit)
   e=hit[0];si,sp,sl,sh=e['source'];kb=sl+nb-e['sink'][2];chain.append(e);nodes.add(si)
   if isrelay(si) and sp in ('o','b'):cur=(si,{'o':'i','b':'a'}[sp],kb % I[si]['ports'][{'o':'i','b':'a'}[sp]]['bits'])
   else:cur=(si,sp,kb);break
  if chain:reset_paths.append(dict(target=[target,cp,0],source=list(cur),edges=chain,qualification='exact source edges; reset age must follow each modeled master, no age inferred from count'))
nodes.add('hb_ckgen')
root=Path('/home/ubuntu/wt/codex-pgstream-cdc-1019');specpath=root/'physical/ref_tile/hbm_su_pg_stream_b_1019/spec.json';spec=json.loads(specpath.read_text());sourcepins={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in spec['sources']}
out=dict(schema='opentallas.hbm.su.record23.topology_profile.v1',qualification='SOURCE-EXPANDED GEN2c+l12 BASIS ONLY; GEN2e pre-relay, S4/S5 not emitted; current source53cb component planned, not parent-qualified',basis=dict(path=str(basis),sha256=hashlib.sha256(basis.read_bytes()).hexdigest(),client=I[client]),paths=paths,reset_paths=reset_paths,instances={n:I[n] for n in sorted(nodes)},clock_resets=[e for e in c['clock_resets'] if e['instance'] in nodes],clock_reset_edges=[e for e in E if e['sink'][0] in nodes and re.search(r'(clk|clock|rst|reset)',e['sink'][1])],straps=[e for e in c['straps'] if e.get('inst') in nodes],basis_rtl_sha256={p:hashlib.sha256((Path('/home/ubuntu/wt/codex-hd4g-strict-1019')/p).read_bytes()).hexdigest() for p in ('rtl/hbm_accel/control/hfd_ckgen.sv','rtl/hbm_accel/die_glue/hbfd_lane_masters.sv','rtl/hbm_accel/die_glue/ot_hbm_lane.sv','rtl/hbm_accel/die_glue/hbfd_pad.sv')},planned_component=dict(revision='53cbcc9a8',spec=str(specpath),spec_sha256=hashlib.sha256(specpath.read_bytes()).hexdigest(),top=spec['top'],params=spec['params'],reset_landing=spec.get('reset_landing'),source_sha256=sourcepins),planned_gen2e_rule='Use real extracted per-direction lane counts as minimum component basis; emitted GEN2e S4/S5 must regenerate/verify paths against new geometry and current reset/clock epochs; pad to budget18/15 or reprice/re-harden if longer. No budget fixture constitutes emitted GEN2e topology.',physical_qualified=False)
p=Path('/home/ubuntu/artifacts/hdie-d4/d4g_gen2e/su_SW0_gen2c_l12_source_profile.json');p.write_text(json.dumps(out,indent=2)+'\n');print(str(p));print(json.dumps(paths,indent=2))
