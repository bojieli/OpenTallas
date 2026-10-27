"""Q6 structural candidates on exact adopted q5b; no cycles/station/core changes."""
import json,sys,copy,hashlib
from pathlib import Path
T=Path(__file__).resolve().parents[2]/'tools/die_plan';sys.path.insert(0,str(T))
import schema as S,gen_phys as G
R=Path(__file__).resolve().parent;src=R/'pd/hm_r26q5b.json';assert hashlib.sha256(src.read_bytes()).hexdigest()=='99b9d6ddfe8937824efead26687709bbfb1e2cc439555a00d211dde7d732dfa6'
raw=json.loads(src.read_text());P=S.Plan(raw,src);selected={'L2090_1','L2158_1'}
while True:
 keys={(P.parts[e['part']]['type'],e['bus']) for pid in selected for e in [P.ports[pid]['src'],P.ports[pid]['dst']] if e['part'] in P.parts}
 new={pid for pid,p in P.ports.items() if any(e['part'] in P.parts and (P.parts[e['part']]['type'],e['bus']) in keys for e in [p['src'],p['dst']])}
 if new<=selected:break
 selected|=new
out=copy.deepcopy(raw);ports={p['id']:p for p in out['ports']};ledger=[]
for pid in sorted(selected):
 p=ports[pid];a,b=p['window_um'];c=(a+b)/2;before=p['window_um'];p['window_um']=[round(c-64,6),round(c+64,6)];ledger.append(dict(port=pid,old=before,new=p['window_um'],reason='Q5 .75GRT 1056-bit entry band overflows; spread registered pins across128um, common replicated-type closure'))
t=out['partition_types']['kv3_sys_c'];before=S.tap_grid(P,'kv3_sys_c');t['clock'].pop('tap_edge_y_um',None)
Q=S.Plan(out,src);after=S.tap_grid(Q,'kv3_sys_c')
(R/'q6_window_tap_delta.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),ports=ledger,type_bus_closure=sorted(keys),sys_c_taps_before=before,sys_c_taps_after=after,cycles_added=0),indent=1)+'\n')
(R/'pd/hm_r26q6_windows.json').write_text(json.dumps(out,indent=1)+'\n');print('ports',len(selected),'types',len({k[0] for k in keys}),'sysc',before,after)
