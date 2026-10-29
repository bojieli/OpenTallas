# HBM-BIND-2 variants on top of h1 (B1s + landing homes).
#  s2  : Codex central counterfactual = every SU residual cell (su_ownership_r3 source_map) in the slice's primary half
#        (records[].primary_counterfactual); the FF fractures stay (all pieces in one half), compose unchanged.
#  h2  : SFU non-store residual (u_core glue, u_vm, u_rst, u_engine/u_arithmetic glue) at the hub landing (b110, L5m/L23m)
#        instead of b113; store residual stays b113.
import json,sys,re
from pathlib import Path
V=sys.argv[1]; R=Path('/srv/opentallas-scratch2/claude/hbm-bind-2-1029'); D=R/V; D.mkdir(exist_ok=True)
a=json.loads((R/'h1/asbuilt_b.json').read_text()); m=json.loads((R/'h1/map_b.json').read_text())
n=0
if V=='s2':
    o=json.loads(Path('/srv/opentallas-scratch2/claude/codex-hbm-bind-0300/su_ownership_r3/ownership.json').read_text())
    prim={r['source_root']:r['primary_counterfactual'] for r in o['records']}
    for k,v in o['source_map']['parts'].items():
        r=k.split('.')[0]
        if r in prim:
            z=prim[r]; cur=m['parts'][k]
            new=[z]+list(cur[1:]) if isinstance(cur,list) else z
            if new!=cur: m['parts'][k]=new; n+=1
    note='s2 central counterfactual (SU residual in primary half %s)'%json.dumps(prim)
elif V=='h2':
    h=json.loads((R/'homes_h1.json').read_text())['parts']
    for k,v in h.items():
        if k.startswith('sfucore_') and '.u_engine.u_memory.' not in k:
            z=v.replace('_b113','_b110'); m['parts'][k]=z; n+=1
    note='h2 SFU non-store residual at b110 (hub landing)'
(D/'map_b.json').write_text(json.dumps(m)); a['map_file']=str(D/'map_b.json'); a['note']='HBM-BIND-2 '+note+' | '+a['note']
(D/'asbuilt_b.json').write_text(json.dumps(a,indent=1)); (D/'out').mkdir(exist_ok=True)
print(V,'changed',n)
