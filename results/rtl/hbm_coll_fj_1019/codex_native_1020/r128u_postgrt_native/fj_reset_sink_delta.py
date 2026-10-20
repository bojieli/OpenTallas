import pathlib,csv,json,sys,inspect
base=pathlib.Path('/audit');sys.path[:0]=[str(base/'current_audit/tools'),str(base/'current_audit/tools/ref_tile')]
import native_census as N
import textbook_lint as T
q=sys.argv[1];roles,libs=N.liberty_roles(sys.argv[2:]);data={}
for stage,tag in [('mapped','baseline_graph'),('postgrt','native_graph')]:
 g=T.Graph();cells={}
 for master,name,pin,net in csv.reader((base/f'fj{q}_{tag}_cells.tsv').open(),delimiter='\t'):
  if name not in cells:cells[name]=[master,name,{}]
  cells[name][2][pin]=[g.net(net)]
 g.cells=[tuple(x) for x in cells.values()]
 for direction,name,net in csv.reader((base/f'fj{q}_{tag}_ports.tsv').open(),delimiter='\t'):g.ports[name]=(direction.lower(),g.net(net))
 acc=[];scope=dict(N.__dict__);scope['acc']=acc
 src=inspect.getsource(N.census)
 needle='        if n > 32:'
 assert needle in src
 src=src.replace(needle,"        if who.startswith('ot_rrs__'):\n            acc.append((who, sorted(endpoints, key=str)))\n"+needle)
 exec(src,scope);report=scope['census'](g,roles)
 rows={}
 for who,eps in acc:
  cells_eps=[]
  for e in eps:
   if isinstance(e[0],int):
    m,n,_=g.cells[e[0]];r=roles[m]['pins'].get(e[1]) or roles[m]['pins'].get(T._base(e[1]));cells_eps.append(dict(instance=n,master=m,pin=e[1],role=r,sequential=roles[m]['sequential']))
   else:cells_eps.append(dict(port=e))
  rows[who]=cells_eps
 data[stage]=dict(status=report['status'],max_dynamic_loads=report['max_dynamic_loads'],role_errors=report['role_errors'],rows=rows,instances=set(cells))
result={}
for who,ends in data['postgrt']['rows'].items():
 if len(ends)<=32:continue
 old=data['mapped']['rows'].get(who,[]);key=lambda r:(r.get('instance','').replace('\\',''),r.get('pin',''))
 before={key(x):x for x in old};after={key(x):x for x in ends};added=[dict(x,birth='newborn' if x.get('instance') not in data['mapped']['instances'] else 'original') for k,x in after.items() if k not in before];removed=[x for k,x in before.items() if k not in after]
 result[who]=dict(mapped_loads=len(old),postgrt_loads=len(ends),added=added,removed=removed,all_actual_sinks=ends)
out=dict(schema='opentallas.codex.reset_sink_delta.v1',graph_authority='actual1_synth/5_1GRT ODB',endpoint_extraction='unchanged mainnativecensus report instrumentation only; no threshold/rule change',liberty=libs,violating_reset_driver_deltas=result)
(base/f'fj{q}_reset_sink_delta.json').write_text(json.dumps(out,indent=2)+'\n')
print(q,json.dumps({k:{'mapped':v['mapped_loads'],'post':v['postgrt_loads'],'added':v['added'],'removed':v['removed']} for k,v in result.items()},indent=2))
