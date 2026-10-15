#!/usr/bin/env python3
"""Exact scalar connectivity/depth of completed bit-mapped FEC (no wire timing)."""
import argparse,array,collections,hashlib,json,pathlib,time
CLOCKS=['clk','clk_collect','clk_encode','clk_codeword','pma_rck','rclk_syndrome','rclk_bm0','rclk_bm1','rclk_bm2','rclk_bm3','rclk_chien','rclk_emit']
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--netlist',type=pathlib.Path,required=True);ap.add_argument('--out',type=pathlib.Path,required=True);ap.add_argument('--clock-manifest',type=pathlib.Path);ap.add_argument('--top',default='hfd_serdes487_chien_linear_window');a=ap.parse_args();started=time.monotonic();clocks=json.loads(a.clock_manifest.read_text())['clocks'] if a.clock_manifest else CLOCKS;assert 0<len(clocks)<31
 raw=a.netlist.read_bytes();digest=hashlib.sha256(raw).hexdigest();m=json.loads(raw)['modules'][a.top];del raw
 cb={m['ports'][c]['bits'][0]:i for i,c in enumerate(clocks)};ff=[];gates=[];types=collections.Counter();maximum=0
 for n,c in m['cells'].items():
  typ=c['type'];types[typ]+=1
  if typ=='$scopeinfo':continue
  ins=tuple(b for p,v in c['connections'].items() if c['port_directions'][p]=='input' for b in v if isinstance(b,int));outs=tuple(b for p,v in c['connections'].items() if c['port_directions'][p]=='output' for b in v if isinstance(b,int))
  maximum=max(maximum,max(ins+outs,default=0))
  if 'DFF' in typ:
   assert typ.startswith('$_') and len(c['connections']['Q'])==1,typ
   clock=c['connections'].get('C',c['connections'].get('CLK'));assert len(clock)==1 and clock[0] in cb,(n,clock)
   ff.append((n,cb[clock[0]],c['connections']['Q'][0],c['connections'].get('D',[None])[0],tuple(b for p,v in c['connections'].items() if p=='E' or (p=='R' and typ.startswith('$_SDFF')) for b in v if isinstance(b,int))))
  else:
   assert typ.startswith('$_') and len(outs)==1,(n,typ,len(outs))
   gates.append((tuple(set(ins)),outs[0],typ))
 pi={p:tuple(b for b in v['bits'] if isinstance(b,int)) for p,v in m['ports'].items() if v['direction']=='input'}
 po={p:tuple(b for b in v['bits'] if isinstance(b,int)) for p,v in m['ports'].items() if v['direction']=='output'}
 qbits={q for n,r,q,d,e in ff};aliases=collections.defaultdict(list)
 for name,v in m.get('netnames',{}).items():
  if v.get('hide_name',0):continue
  for offset,bit in enumerate(v['bits']):
   if bit in qbits:aliases[bit].append(f'{name}[{offset+v.get("offset",0)}]')
 ffq={n:q for n,r,q,d,e in ff}
 del m
 size=maximum+1;driver=array.array('i',[-1])*size;srcmask=array.array('I',[0])*size;dstmask=array.array('I',[0])*size;depth=array.array('I',[0])*size;uses=array.array('I',[0])*size;ffcounts=collections.Counter()
 for _,root,q,d,enable in ff:
  assert isinstance(q,int);srcmask[q]|=1<<root;ffcounts[root]+=1
  if isinstance(d,int):dstmask[d]|=1<<root
  for e in enable:dstmask[e]|=1<<root
 for name,bits in pi.items():
  if name in clocks:continue
  for b in bits:srcmask[b]|=1<<len(clocks)
 consumers=collections.defaultdict(list)
 for idx,(ins,out,typ) in enumerate(gates):
  assert driver[out]==-1;driver[out]=idx
  for b in ins:consumers[b].append(idx);uses[b]+=1
 indegree=array.array('I',[0])*len(gates)
 for idx,(ins,out,typ) in enumerate(gates):indegree[idx]=sum(driver[b]>=0 for b in ins)
 ready=collections.deque(i for i,n in enumerate(indegree) if n==0);order=array.array('I')
 while ready:
  idx=ready.popleft();order.append(idx);ins,out,typ=gates[idx];mask=0;high=0
  for b in ins:mask|=srcmask[b];high=max(high,depth[b])
  srcmask[out]=mask;depth[out]=high+1
  for child in consumers.get(out,()):
   indegree[child]-=1
   if indegree[child]==0:ready.append(child)
 assert len(order)==len(gates),f'Combinational cycle/unresolved graph: {len(gates)-len(order)}'
 for idx in reversed(order):
  ins,out,typ=gates[idx]
  for b in ins:dstmask[b]|=dstmask[out]
 roots={};cross=[]
 for i,root in enumerate(clocks):
  rows=[f for f in ff if f[1]==i];data=[(depth[d],n,srcmask[d]) for n,r,q,d,e in rows if isinstance(d,int)];enable=[(depth[b],n,srcmask[b]) for n,r,q,d,e in rows for b in e];incoming=collections.Counter();outgoing=collections.Counter()
  for n,r,q,d,e in ff:
   if dstmask[q]&(1<<i):incoming[clocks[r]]+=1
  for n,r,q,d,e in rows:
   for dest in range(len(clocks)):
    if dstmask[q]&(1<<dest):outgoing[clocks[dest]]+=1
  roots[root]={'flop_bits':len(rows),'max_D_logic_levels':max((d for d,_,_ in data),default=0),'max_enable_or_sync_reset_logic_levels':max((d for d,_,_ in enable),default=0),'top_D_paths':[{'levels':d,'sink_cell':n,'sink_register_aliases':sorted(aliases[ffq[n]])[:6],'source_roots':[clocks[k] if k<len(clocks) else 'external_input' for k in range(len(clocks)+1) if mask&(1<<k)]} for d,n,mask in sorted(data,reverse=True)[:8]],'registered_source_Q_bits_exact':dict(incoming),'registered_destination_roots_Q_bits_exact':dict(outgoing),'max_Q_fanout':max((uses[q] for n,r,q,d,e in rows),default=0),'D_distinct_net_bits':len({d for n,r,q,d,e in rows if isinstance(d,int)})}
  for target,bits in outgoing.items():
   if target!=root:cross.append({'source_root':root,'sink_root':target,'distinct_registered_source_bits':bits})
 unique=collections.Counter();shared=collections.Counter();orphan=0
 for ins,out,typ in gates:
  mask=dstmask[out]
  if not mask:orphan+=1
  elif mask&(mask-1):shared[typ]+=1
  else:unique[clocks[mask.bit_length()-1]]+=1
 res={'scope':'ACTUAL_SCALAR_NETLIST_CONNECTIVITY_AND_LOGIC_DEPTH_NO_PHYSICAL_TIMING','input_sha256':digest,'tool_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'total_flop_bits':len(ff),'clock_roots':roots,'scalar_cells_by_type':dict(types),'combinational_scalar_cells':len(gates),'comb_cells_requiring_each_sink_root':{clocks[i]:sum(bool(dstmask[out]&(1<<i)) for ins,out,typ in gates) for i in range(len(clocks))},'unique_sink_root_comb_cells':dict(unique),'multi_sink_root_shared_comb_cells_by_type':dict(shared),'no_registered_sink_comb_cells':orphan,'cross_root_registered_relations':cross,'external_ports':{p:{'width':len(v),'registered_sink_roots':{clocks[k]:sum(bool(dstmask[b]&(1<<k)) for b in v) for k in range(len(clocks)) if any(dstmask[b]&(1<<k) for b in v)}} for p,v in pi.items() if p not in clocks},'external_output_logic_levels':{p:max((depth[b] for b in v),default=0) for p,v in po.items()},'limits':['Scalar generic logic levels are not library delay','Edges count distinct source bits, not wire length or physical pins','All D, clock-enable and synchronous-reset cones counted; asynchronous reset delivery is separate','Shared combinational cells require explicit owner or priced replication','Standalone scope excludes joined endpoint and gearbox'],'physical_qualified':False,'elapsed_seconds':time.monotonic()-started}
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(res,indent=2)+'\n');print(json.dumps({'flops':len(ff),'comb_gates':len(gates),'depths':{r:x['max_D_logic_levels'] for r,x in roots.items()},'elapsed':res['elapsed_seconds']}))
if __name__=='__main__':main()
