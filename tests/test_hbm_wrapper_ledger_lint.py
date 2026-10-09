"""Internal wrapper ties must remain visible even when external connectivity is complete."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from die_top_lint import hbm_wrapper_ledgers


def view(root, master='hfd_test'):
    path = root / 'physical/hbm_accel_die_views/test/rtl'
    path.mkdir(parents=True)
    (path / 'spec.json').write_text(json.dumps({'master': master}))
    (path / f'{master}.sv').write_text('current wrapper\n')
    return path


def test_internal_tie_report_and_source_identity(tmp_path):
    path = view(tmp_path)
    def generate(spec, strict):
        assert strict is False
        return 'current wrapper\n', dict(ties=[{'where': 'core.result', 'gap': 'TIED_OFF', 'bits': 64}],
                tied_off_bits=64, classed_tie_bits={}, errors=['core.result: folded'])
    ledger = hbm_wrapper_ledgers({'hfd_test'}, tmp_path, generate)
    assert ledger['tied_off_bits'] == 64 and ledger['wrappers_with_errors'] == 1
    row = ledger['wrappers'][0]
    assert row['wrapper_matches_spec']
    assert row['spec_sha256'] == hashlib.sha256((path / 'spec.json').read_bytes()).hexdigest()
    assert row['wrapper_sha256'] == hashlib.sha256((path / 'hfd_test.sv').read_bytes()).hexdigest()
    assert row['ties'][0]['gap'] == 'TIED_OFF'


def test_failed_ledger_is_unknown_not_zero_or_matching(tmp_path):
    view(tmp_path)
    def generate(spec, strict):
        raise SystemExit('missing port')
    ledger = hbm_wrapper_ledgers({'hfd_test'}, tmp_path, generate)
    assert ledger['generation_failures'] == ledger['wrappers_with_errors'] == 1
    assert ledger['wrappers'][0]['tied_off_bits'] is None
    assert not ledger['wrappers'][0]['wrapper_matches_spec']
    assert 'missing port' in ledger['wrappers'][0]['errors'][0]


def test_retired_master_not_counted_and_stale_wrapper_visible(tmp_path):
    view(tmp_path)
    def generate(spec, strict):
        return 'new wrapper\n', dict(ties=[], tied_off_bits=0, classed_tie_bits={})
    assert not hbm_wrapper_ledgers({'other'}, tmp_path, generate)['wrappers']
    ledger = hbm_wrapper_ledgers({'hfd_test'}, tmp_path, generate)
    assert ledger['wrappers_matching_spec'] == 0
