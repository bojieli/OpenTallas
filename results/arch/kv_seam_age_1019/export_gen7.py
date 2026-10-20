import json, pathlib, sys, hashlib
base=pathlib.Path('/srv/opentallas-scratch/claude/qwen-kvsys')
r=base/'kvs14r-4db097403-codexmub'; w=base/'wt-kvs14r-4db097403-codexmub'
o=base/'codex-canonical-landlag/gen7-seam'; b=base/'codex-canonical-landlag/gen7_bind_r1'
sys.path[:0]=[str(o/'tools/qwen_layerbench'),str(o/'tools'),str(w/'tools'),str(w/'tools/qwen_split')]
import netlist_relay_stages as N
import die_relay_stages as D
N.ROOT=w
pb=json.load((r/'port_bind_v2/port_bind_v2.json').open())
for row in pb['masters'].values():
 if row.get('rtl') and not pathlib.Path(row['rtl']).is_absolute():row['rtl']=str(w/row['rtl'])
pb['rtl_files']=[str(w/f) if not pathlib.Path(f).is_absolute() else f for f in pb.get('rtl_files',[])]
d=N.export(str(b/'die_bound.v'),pb,'qwen_kv','4db0974030714ac3f3745ccadd6c0a234dfeb3c4',[str(w)+'/',str(r)+'/',str(b)+'/'],[str(r/'port_bind_v2'),str(b)],'kvs14r-4db097403-codexmub',reach=405,land_e=N.export_lanes(r/'fwd_lanes.json'))
D.write(o/'kv_table.gen7.json',d)
paths=[r/'fwd_lanes.json',r/'case_kv/land_lag.json',b/'die_bound.v',o/'kv_table.gen7.json',o/'tools/qwen_layerbench/netlist_relay_stages.py',o/'tools/die_relay_stages.py']
m=dict(schema='codex.actual_gen7.seam_proof.v1',qualified_release=False,die_source='4db097403',native_binder_source='c0cec47ae',exporter_source='6a193a942 (exporter only; differs05e bysrc_nets preservation)',bus_count=d['bus_count'],problem_count=d['problem_count'],problems=d['problems'],sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},limitations=['Actual source case; zero unknown ages does not close functional unread/open outputs, native clock/phase, reset/fault retirement or stand-in view gaps.'])
(o/'proof.json').write_text(json.dumps(m,indent=1)+'\n')
print(json.dumps(dict(bus_count=d['bus_count'],problem_count=d['problem_count'],problems=d['problems'][:10])))
