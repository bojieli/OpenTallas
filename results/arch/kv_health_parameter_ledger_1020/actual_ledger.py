import json,hashlib,os
from pathlib import Path
import kv_health_plane as H
import kv_expand_parameters as E
import die_port_bind as P
R=Path('/srv/opentallas-scratch/claude/qwen-kvsys/kvs14r-54e9d9c39-gen9d5p')
S=Path('/srv/opentallas-scratch/claude/qwen-kvsys/wt-kvs14r-54e9d9c39-gen9d5p')
h=json.loads((R/'health_plane.json').read_text());r=json.loads((R/'expand.json').read_text());ip=json.loads((R/'case_kv/die.v.params.json').read_text())
os.environ['OT_KV_PARAM_DIAG']='1'
rows,sidecar=H.parameter_ledger(S,h['plan'],{},True)
assert not(set(rows)&set(r.get('parameter_instances',{})))
assert not(set(sidecar)&set(ip))
r.setdefault('parameter_instances',{}).update(rows);ip.update(sidecar)
inst=P.parse_die(str(R/'case_kv/die.v'))[3]
pre=R/'case_kv/die.v.preexp'
original={i:m for m,i,p,c in P.parse_die(str(pre))[3] if m!='__assign__'} if pre.exists() else {}
sources={m:b['rtl'] for m,b in r['leaves'].items()}
E.verify_bound(S,r,ip,inst,sources,original,True)
q=dict(schema='opentallas.health_parameter_repair_actual.v1',qualified=False,source_commit=(R/'case_kv/SOURCE_COMMIT').read_text().strip(),run=str(R),source_root=str(S),added=len(rows),masters=sorted(set(v['module'] for v in rows.values())),all_unqualified=all(not v['profile']['native_qualified'] for v in rows.values()),independent_enumerator='PASS',inputs={str(x.relative_to(R)):hashlib.sha256(x.read_bytes()).hexdigest() for x in [R/'health_plane.json',R/'expand.json',R/'case_kv/die.v',R/'case_kv/die.v.params.json']})
Path('actual_expand.json').write_text(json.dumps(r,indent=1)+'\n');Path('actual_params.json').write_text(json.dumps(ip,indent=1)+'\n');Path('actual_receipt.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True)
