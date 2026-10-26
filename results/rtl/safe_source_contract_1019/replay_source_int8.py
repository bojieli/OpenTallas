"""Diagnostic source-only positive ordinary-root predicate; overall HOLD required."""
import gzip
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools/closure_loop'))
import safe_source_contract as S
root=Path(sys.argv[1]).resolve(); source=Path(sys.argv[2]).resolve(); out=Path(sys.argv[3]).resolve()
out.mkdir(parents=True,exist_ok=True)
data=source.read_bytes()
S.require(hashlib.sha256(data).hexdigest()=='8e4fdb42a22d755e7efb9cfcdf1ac0efe1563ee500d177e2d8e810fd15b85d27','source mapped graph changed')
netlist=json.loads(data);top='ot_smh_int8_tile_safe'
used={c['type'] for c in netlist['modules'][top]['cells'].values()}
libs=[root/n for n in ('asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz','asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz',
'asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz','asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib','asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz')]
expected={line.split()[1].lstrip('*'):line.split()[0] for line in(root/'SHA256SUMS').read_text().splitlines()}
for path in libs:S.require(S.sha(path)==expected[path.name],f'native library changed {path}')
result=S.census(netlist,top,S.native_cells(libs,used_masters=used))
result['diagnostic_provenance']=dict(source_commit='da40a2a46',mapped_sha256=hashlib.sha256(data).hexdigest(),
 libraries=[dict(path=p.name,sha256=S.sha(p))for p in libs],collector_sha256=S.sha(S.__file__),replay_sha256=S.sha(__file__),
 scope='source-only predicate; no gate/route/production activation')
with gzip.open(out/'source-census.json.gz','wt')as f:json.dump(result,f,sort_keys=True)
summary={k:v for k,v in result.items() if k not in('drivers','input_registration','output_ownership')}
summary['literal_roots']=[r for r in result['drivers'] if r['driver'].startswith('literal:')]
summary['unregistered_data_input_ports']=[r for r in result['input_registration'] if not r['registered_data_endpoints_only'] and r['endpoint_roles'].get('data',0)]
summary['non_ff_output_ports']=[r for r in result['output_ownership'] if not r['registered']]
(out/'source-summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:v for k,v in summary.items()if k!='literal_roots'},indent=2,sort_keys=True))
S.require(result['verdict']=='HOLD' and not result['violations'],'source must remain physicalization HOLD')
S.require(result['max_nonliteral_loads']==24,'ordinary source maximum changed')
S.require({r['driver']:r['loads']for r in summary['literal_roots']}=={'literal:0':64,'literal:1':202},'literal inventory changed')
S.require(not summary['unregistered_data_input_ports'] and not summary['non_ff_output_ports'],'source boundary ownership changed')
print('SOURCE_ORDINARY_PREDICATE_PASS OVERALL_HOLD literals64/202 max_nonliteral24')
