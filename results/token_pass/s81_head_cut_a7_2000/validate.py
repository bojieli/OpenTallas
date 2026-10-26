"""Validate collected CUT-A evidence only; never reclassify the raw head result."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
binary = 'ef0e1d076b96233b8a1559b1fdf85a035edacea9a4e39ac2dbe653f82d98845d'
raw = json.loads((HERE/'raw/result.json').read_text())
a = json.loads((HERE/'raw/a.json').read_text())
identity = json.loads((HERE/'identity.json').read_text())
assert raw['ok'] is False and set(raw['cases']) == {'a','a_mut'}
assert raw['cases']['a']['verdict'] == 'PASS'
assert raw['cases']['a_mut']['verdict'] == 'FAIL'
assert a['tiles'] == a['pass_'] == len(a['tiles_detail']) == 253
assert a['lats'] == [8345]
for name, result in a['tiles_detail'].items():
    log = (HERE/'raw/a'/name/'run.log').read_text()
    assert result['ok'] is True and result['logits'] == 'LOGITS 128/128'
    assert int(result['rec'][0]) == 8345 and int(result['rec'][3]) == 0
    assert 'LOGITS 128/128' in log and 'PASS tilecut' in log and 'FAIL' not in log
mut = (HERE/'raw/a_mut/u_t_S01Er3/run.log').read_text()
assert 'FAIL tilecut row 21993 != 21946' in mut
assert len((HERE/'raw/rec.hex').read_text().split()) == 253
assert (HERE/'build/original_binary.sha256').read_text().split()[0] == binary
assert (HERE/'compat_identity.sha256').read_text().split()[0] == binary
assert any(f['sha256'] == binary and f['path'].endswith('Vtb_s81hd_tilecut') for f in identity['files'])
for line in (HERE/'original_build_inputs.sha256').read_text().splitlines():
    digest, name = line.split(maxsplit=1)
    if name.endswith('.sv') or Path(name).name in ('die.v','port_bind.json'):
        assert any(Path(f['path']).name == Path(name).name and f['sha256'] == digest
                   for f in identity['files']), 'original bound source changed: '+name
assert 'RAN on ot-gold1 (unit oth-ubuntu-659357-1792640255): exit 0' in (HERE/'compat.otrun.log').read_text()
hashes = {str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest()
          for p in sorted(HERE.rglob('*')) if p.is_file() and p.name != 'receipt.json'}
receipt = dict(schema='opentallas.s81.head_cut_a_component.v1', status='PARTIAL_HEAD_CUT_A_PASS',
    scope='253 independent production tile CUT-A executions; CUT-B absent',
    tile_pass=253, tile_count=253, exact_logits_per_tile=128, exact_logits_total=253*128,
    bundle_latency_stream_edges=8345, mutant='wrong tile ROM images rejected',
    source_recovery_commit='72bea18b900ec722de4d5ee9d56dbabd481db83b',
    binary_sha256=binary, binary_reused=True, new_compile=False,
    runtime='task-local gold1 loader and four shared libraries; identities only committed',
    raw_result_preserved_ok=False, raw_result_scope='full head report remains incomplete without CUT-B',
    complete_head=False, complete_layer=False, complete_token=False,
    fleet_unit='oth-ubuntu-659357-1792640255', fleet_exit=0,
    original_environment_failure='original_environment_failure/a retains PVE1 loader/version failures',
    artifacts_sha256=hashes)
(HERE/'receipt.json').write_text(json.dumps(receipt,indent=1)+'\n')
print('CUT_A_COMPONENT_PASS 253/253 tiles; 32384/32384 logits; causal mutant rejected; PARTIAL head')
