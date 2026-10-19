import json,gzip,sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path('tools/hbm_hidx_coupon1/oracle/closure_loop').resolve()))
import safe_source_contract as S
j=json.loads(Path('out/netlist.json').read_text());m=j['modules']['hidx_coupon1']
scopes={n:c for n,c in m['cells'].items() if c['type']=='$scopeinfo'}
assert all(not c['connections'] for c in scopes.values())
m['cells']={n:c for n,c in m['cells'].items() if n not in scopes}
p=Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM')
libs=[next(p.glob('asap7sc7p5t_'+f+'_RVT_TT_*.lib.gz')) for f in ['AO','INVBUF','OA','SIMPLE']]+[p/'asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib']
r=S.census(j,'hidx_coupon1',S.native_cells(libs,used_masters={c['type'] for c in m['cells'].values()}))
r['diagnostic_provenance']=dict(oracle_commit='969965293',scope_metadata_only=scopes,graph_sha256=S.sha('out/netlist.json'),libraries=[dict(path=str(p),sha256=S.sha(p)) for p in libs],oracle_sha256=S.sha(S.__file__))
with gzip.open('out/strict_census.json.gz','wt')as f:json.dump(r,f,sort_keys=True)
s={k:v for k,v in r.items() if k not in ['drivers','input_registration','output_ownership','diagnostic_provenance']};s['non_ff_output_count']=sum(not x['registered'] for x in r['output_ownership']);s['input_non_dataff_count']=sum(not x['registered_data_endpoints_only'] and x['endpoint_roles'].get('data',0)>0 for x in r['input_registration'])
Path('out/strict_summary.json').write_text(json.dumps(s,indent=2)+'\n');print(json.dumps(s,indent=2))
