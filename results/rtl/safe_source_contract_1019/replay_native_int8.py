"""Read-only diagnostic replay of faithful raw OpenDB export, not a NEW-kit flag.

PG omissions depend on actual exported MTerm signal roles, checked against both
instance pin roles and native master pin roles. Every other connection survives.
"""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools/closure_loop'))
import safe_source_contract as S

root=Path(sys.argv[1]).resolve()
out=Path(sys.argv[2]).resolve(); out.mkdir(parents=True, exist_ok=True)
rawpath=root/'raw.json'; rawbytes=rawpath.read_bytes(); raw=json.loads(rawbytes)
S.require(hashlib.sha256(rawbytes).hexdigest()=='7ae2cc0705d6369853e46ce46218ab26c92f2d6f9ae7bff334b5e03ee5bba54b','raw export changed')
S.require(raw['source_odb_sha256']=='3e3d3df1b4247ba46b8c6d0388e84fdda89675351d314cb8165eb7329d923f19','ODB identity changed')
expected={line.split()[1].lstrip('*'):line.split()[0] for line in (root/'SHA256SUMS').read_text().splitlines()}
libs=sorted(root.glob('*.lib*'))
for path in [rawpath]+libs:
    S.require(path.name in expected and S.sha(path)==expected[path.name],f'export manifest mismatch {path.name}')
mod=raw['modules']['ot_smh_int8_tile']; removed=Counter(); physical=[]
for name,p in list(mod['ports'].items()):
    S.require('signal_type' in p,f'unknown port role {name}')
    if p['signal_type'] in ('POWER','GROUND'):
        removed['top_pg_pins']+=len(p['bits']); del mod['ports'][name]
for name,c in list(mod['cells'].items()):
    pins=raw['native_master_pins'][c['type']]
    S.require(set(c['connections'])==set(c['port_directions'])==set(c['pin_signal_types'])==set(pins),f'pin inventory mismatch {name}')
    for pin in list(c['connections']):
        S.require(c['pin_signal_types'][pin]==pins[pin]['signal_type'] and c['port_directions'][pin]==pins[pin]['direction'],f'native role mismatch {name}/{pin}')
        if pins[pin]['signal_type'] in ('POWER','GROUND'):
            removed['instance_pg_pins']+=len(c['connections'][pin])
            del c['connections'][pin]; del c['port_directions'][pin]
    if not c['connections']:
        physical.append(dict(instance=name,master=c['type'])); del mod['cells'][name]
# Gate directory also carries three unused FAKE bundle models. This replay
# parses the exact five real ASAP7 native libraries; every used master still
# has to resolve in those libraries, or census refuses it. No graph cell is skipped.
parsed_libs=[root/n for n in (
    'asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz',
    'asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz',
    'asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz',
    'asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib',
    'asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz')]
start=time.monotonic(); native=S.native_cells(parsed_libs, used_masters={c['type'] for c in mod['cells'].values()}); result=S.census(raw,'ot_smh_int8_tile',native)
result['diagnostic_provenance']=dict(raw_export_sha256=hashlib.sha256(rawbytes).hexdigest(),source_odb_sha256=raw['source_odb_sha256'],
    source_odb=raw['source_odb'], pg_only_native_master_pins={p['master']:raw['native_master_pins'][p['master']] for p in physical}, input_manifest_sha256=S.sha(root/'SHA256SUMS'),
    libraries=[dict(path=p.name,sha256=S.sha(p),parsed=p in parsed_libs) for p in libs],collector_sha256=S.sha(S.__file__),
    replay_sha256=S.sha(__file__),physical_omissions=dict(removed),pg_only_instances=physical,
    comparison_scope='old-kit read-only diagnostic API; not NEW-kit activation',elapsed_seconds=time.monotonic()-start)
with gzip.open(out/'census.json.gz','wt') as f:json.dump(result,f,sort_keys=True)
summary={k:v for k,v in result.items() if k not in ('drivers','input_registration','output_ownership','diagnostic_provenance')}
summary['violating_roots']=[{k:v for k,v in r.items() if k not in ('endpoints','clock_endpoints')} for r in result['drivers'] if r['driver'] in result['violations']]
summary['diagnostic_provenance']=result['diagnostic_provenance']
canonical=[r for r in result['drivers'] if r['driver'] in result['violations'] and not r['transparent']]
summary['canonical_nontransparent_violators']=len(canonical)
summary['transparent_output_violators']=len(result['violations'])-len(canonical)
(out/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
print(json.dumps(summary,indent=2,sort_keys=True))
S.require(result['verdict']=='FAIL','known unsafe native source must fail')
S.require(len(canonical)==17,'independent native canonical unsafe root count changed')
S.require(all(r['role']=='ff' for r in canonical),'canonical unsafe native roles changed')
print('REAL_NATIVE_EXPECTED_FAIL_CONFIRMED 17 canonical; all-driver violations',len(result['violations']))
