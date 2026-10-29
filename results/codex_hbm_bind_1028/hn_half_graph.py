"""Export exact intended HN physical-half ownership and directed source bits.

Usage: hn_half_graph.py SOURCE_BASE ASBUILT_JSON TOP OUT
This reads existing E elaboration only. No production source selection or layout.
"""
from pathlib import Path
import collections,json,re,sys
base,src,top,out=sys.argv[1:];sys.path.insert(0,str(Path(base)/'tools/die_plan'))
import bind_elab as E
f=E.flatten(json.loads(Path(src).read_text()),top,retain_hierarchy_ports=True)
h={p:v for p,v in f.instances.items() if re.search(r'\.u_pair\.u_h[ns]$',p)}
assert len(h)==32 and collections.Counter(v['master'] for v in h.values())=={'hnx_rp3lp3h_n':16,'hnx_rp3lp3h_s':16}
q=collections.Counter();res=[]
for c in f.cells:
 if not any(s in c.module.lower() for s in ('dff','latch')):continue
 owners=[p for p in h if c.path.startswith(p+'.')]
 row=dict(path=c.path,module=c.module,q_bits=len(c.ports.get('Q',[])))
 if len(owners)!=1:res.append(row)
 else:q[owners[0]]+=row['q_bits']
drv=collections.defaultdict(list);snk=collections.defaultdict(list)
for p,v in h.items():
 for pn,port in v['ports'].items():
  if pn in ('ck_n','ck_s','clk','rst_n','rst_a'):continue
  tab=drv if port['dir']=='output' else snk
  for i,b in enumerate(port['bits']):
   if isinstance(b,int):tab[b].append((p,pn,i))
edges=collections.defaultdict(list);amb=[]
for b,sinks in snk.items():
 drivers=drv.get(b,[])
 if len(drivers)>1:amb.append(dict(net=b,drivers=drivers,sinks=sinks));continue
 if not drivers:continue
 sp,port,bit=drivers[0]
 for dp,dport,dbit in sinks:
  edges[(sp,port,dp,dport)].append(dict(source_bit=bit,sink_bit=dbit,global_net=b))
r=dict(schema='opentallas.hbm.native_hn_physical_half_graph.v1',source_json=src,top=top,
 half_instances=h,per_half_internal_q_bits=dict(q),total_half_internal_q_bits=sum(q.values()),
 residual_parent_state=res,residual_parent_q_bits=sum(c['q_bits'] for c in res),
 edges=[dict(source=s,source_port=sp,sink=d,sink_port=dp,bit_pairs=bits) for (s,sp,d,dp),bits in sorted(edges.items())],
 multiple_driver_nets=amb,note='Actual32physicalwholehalfcut; internal state belongs to hard halves. New backend ABI candidate only, no current150front/adoption/latency or geometric inference.')
Path(out).write_text(json.dumps(r,separators=(',',':'))+'\n');print('HN physical halves',len(h),'internalQ',sum(q.values()),'parentQ',r['residual_parent_q_bits'],'directed groups',len(edges),'multi',len(amb))
