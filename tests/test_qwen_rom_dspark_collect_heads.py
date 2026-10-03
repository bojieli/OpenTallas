import hashlib
import json
from pathlib import Path

import pytest

from tools.qwen_rom_dspark_collect_heads import collect


def fixture_stream(tmp_path):
    stream, source = tmp_path / 'stream', tmp_path / 'source'
    source.mkdir()
    (source / 'core.sv').write_text('pinned')
    pins = {'core.sv': hashlib.sha256(b'pinned').hexdigest()}
    (stream / 'res').mkdir(parents=True)
    for p in (1, 4):
        oracle = {'heads': [{'argmax_token': j + 10, 'logit_bits': '3f800000'} for j in range(p)]}
        directory = stream / f'head_oracle_p{p}'
        directory.mkdir()
        op = directory / 'oracle.json'
        op.write_text(json.dumps(oracle))
        tokens = ' '.join(f't{j}={j+10}/3f800000' for j in range(p))
        result = {'status': 'pass', 'source_stable': True, 'stages_run': ['head'],
                  'design_point': {'tp': 4}, 'wire_stages': {'bd': 41},
                  'verify': {'positions': p, 'vpos': 1, 'enable_arp': 1,
                             'per_die_tokens': {str(d): tokens for d in range(4)}},
                  'total_cycles': 100 * p, 'source_sha256': pins,
                  'oracle_sha256': hashlib.sha256(op.read_bytes()).hexdigest()}
        (stream / 'res' / f'head{p}.json').write_text(json.dumps(result))
        (stream / f'head{p}.rc').write_text('0\n')
    return stream, source


def test_measured_pair_and_immutable_output(tmp_path):
    stream, source = fixture_stream(tmp_path)
    out = tmp_path / 'result'
    summary = collect(stream, source, out)
    assert summary['status'] == 'PASS'
    assert summary['increment_per_extra_position'] == 100
    assert (out / 'head4' / 'head4.json').exists()
    with pytest.raises(FileExistsError):
        collect(stream, source, out)


@pytest.mark.parametrize('mutation', ['missing_rank', 'logit', 'source', 'wire', 'failed_runner'])
def test_false_pass_and_failed_runner_preserved(tmp_path, mutation):
    stream, source = fixture_stream(tmp_path)
    path = stream / 'res' / 'head4.json'
    record = json.loads(path.read_text())
    if mutation == 'missing_rank':
        del record['verify']['per_die_tokens']['3']
    elif mutation == 'logit':
        record['verify']['per_die_tokens']['3'] = record['verify']['per_die_tokens']['3'].replace('3f800000', '3f800001')
    elif mutation == 'source':
        (source / 'core.sv').write_text('changed')
    elif mutation == 'wire':
        record['wire_stages']['bd'] = 40
    elif mutation == 'failed_runner':
        (stream / 'head4.rc').write_text('1\n')
        path.unlink()
    if mutation != 'failed_runner':
        path.write_text(json.dumps(record))
    out = tmp_path / 'result'
    summary = collect(stream, source, out)
    assert summary['status'] == 'FAIL'
    assert summary['increment_per_extra_position'] is None
    assert summary['jobs']['head4']['errors']
    assert (out / 'head4' / 'head4.rc').exists()
