import hashlib
import json
import shutil
import time

import pytest

from lec_official_import import prepare


def fixture(tmp_path):
    k = tmp_path / 'original'
    k.mkdir()
    (k / 'rtl').mkdir()
    contents = {'rtl/top.v': 'module top;endmodule', 'config.mk': 'export VERILOG_FILES = /work/rtl/top.v\n',
                'freeze.json': '{"schema":"core.v1"}', 'lec.py': '# official checker', 'net.v': 'module top;endmodule'}
    for n, body in contents.items():
        (k / n).write_text(body)
    hashes = {n: hashlib.sha256((k / n).read_bytes()).hexdigest() for n in contents if n != 'net.v'}
    (k / 'PROVENANCE.json').write_text(json.dumps({'provenance': {'commit': 'a' * 40, 'dirty': False}, 'files': hashes}))
    (k / 'lec').mkdir()
    (k / 'lec/lec.json').write_text('{"verdict":"UNPROVEN"}')
    c = tmp_path / 'copy'
    shutil.copytree(k, c)
    p = tmp_path / 'official'
    p.mkdir()
    (p / 'hints.json').write_text('{"hints":[]}')
    (p / 'hyp.json').write_text('{}')
    time.sleep(.005)
    report = {'schema': 'opentallas.lec.v1', 'verdict': 'EQUIVALENT', 'netlist': '/work/net.v',
              'counts': {'compare_points': 123, 'proved': 123, 'differs': 0, 'undecided': 0},
              'reset_contract': {'default': 4, 'used': 4, 'requested': 4, 'contract': None, 'debug_overrides': {}},
              'kept_registers': {'missing': {'n': 0}},
              'provenance': {'commit': 'a' * 40, 'dirty': False, 'source': 'validated kit PROVENANCE.json'},
              'hints': {'sha256': hashlib.sha256((p / 'hints.json').read_bytes()).hexdigest()}}
    (p / 'lec.json').write_text(json.dumps(report))
    log = tmp_path / 'producer.log'
    log.write_text('ot-run: RAN on intel1 (unit oth-good-1): exit 0\n')
    return dict(original=k, proof=p, copied=c, producer_log=log, producer_unit='oth-good-1', checker_sha256=hashes['lec.py'], reset_cycles=4)


def test_official_intake_preserves_failed_original_and_receipt(tmp_path):
    args = fixture(tmp_path)
    original = (args['original'] / 'lec/lec.json').read_bytes()
    receipt = (args['proof'] / 'lec.json').read_bytes()
    d = prepare(**args)
    assert not d['source_qualified'] and not d['historical_async_lease']
    assert (args['original'] / 'lec/lec.json').read_bytes() == original
    assert (args['copied'] / 'lec_before_official_import/lec.json').read_bytes() == original
    assert (args['copied'] / 'lec/lec.json').read_bytes() == receipt
    assert prepare(**args) == d


@pytest.mark.parametrize('mutation', ['source', 'netlist', 'checker', 'hints', 'receipt', 'exit', 'reset', 'pid'])
def test_refuse_unqualified_or_changed_intake_before_mutation(tmp_path, mutation):
    a = fixture(tmp_path)
    if mutation in ('source', 'netlist', 'checker'):
        name = {'source': 'rtl/top.v', 'netlist': 'net.v', 'checker': 'lec.py'}[mutation]
        (a['copied'] / name).write_text('changed')
    elif mutation == 'hints':
        (a['proof'] / 'hints.json').write_text('changed')
    elif mutation == 'receipt':
        d = json.loads((a['proof'] / 'lec.json').read_text())
        d['counts']['undecided'] = 1
        (a['proof'] / 'lec.json').write_text(json.dumps(d))
    elif mutation == 'exit':
        a['producer_log'].write_text('(unit oth-good-1): exit 1\n')
    elif mutation == 'reset':
        a['reset_cycles'] = 64
    else:
        (a['copied'] / 'lec_async.pid').write_text('123')
    before = (a['copied'] / 'lec/lec.json').read_bytes()
    with pytest.raises(ValueError):
        prepare(**a)
    assert (a['copied'] / 'lec/lec.json').read_bytes() == before
    assert not (a['copied'] / 'lec_async.official_import.json').exists()
