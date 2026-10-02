import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import run_w17_D1_native_diagnostic as diagnostic
import w17_D1_native_join as join

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'results/uarch/w17_D1_disjoint_native_actual_runtime_20261002_r1'
def load(path):
    return json.loads((DATA / path).read_text())

def test_actual_runtime_failure_cannot_be_promoted_by_native_link_pass():
    actual = load('runtime/receipt.json')
    text = (DATA / 'runtime/runtime.log').read_text()
    assert load('join/receipt.json')['verdict'] == 'PASS_NATIVE_PREFIX_LINK_ONLY'
    assert diagnostic.classify(text, actual['exit_code'])['verdict'] == 'FAIL_DIAGNOSTIC_RUNTIME'
    assert diagnostic.classify(text, 0)['verdict'] == 'FAIL_DIAGNOSTIC_RUNTIME'
    assert actual['postcheck'] is True
    assert 'D1_PREFIX_GATE_AND_FIRST_RETURN_ONLY' not in text
    assert 'D1_REAL_ACCEPT ' not in text and 'D1_REAL_RESPONSE ' not in text
    assert 'D1_SOURCE_OR_LEDGER_FAULT' in text

def test_both_actual_terminal_sets_cover_original_archive_exactly():
    local = load('local/object_identity.json')
    remote = load('VM/object_identity.json')
    ordered = load('join/ordered_objects.json')
    join.receipt_valid(load('local/verdict.json'), 'local')
    join.receipt_valid(load('VM/verdict.json'), 'VM')
    a = {x['target']: x['SHA256'] for x in local['objects']}
    b = {x['target']: x['SHA256'] for x in remote['objects']}
    assert len(a) == 1286 and len(b) == 2543 and not set(a) & set(b)
    assert len(ordered) == len({x['target'] for x in ordered}) == 3829
    for row in ordered:
        assert row['sha256'] == (a if row['owner'] == 'local' else b)[row['target']]
    assert local['retained_objects_byteidentical'] == remote['retained_local_objects_byteidentical'] == 252
    assert local['retained_PCH_byteidentical'] == remote['retained_PCH_byteidentical'] == 2

def test_actual_archive_dryrun_has_no_hidden_recompilation():
    text = (DATA / 'join/archive_dryrun.log').read_text()
    assert join.compiler_targets(text) == []
    assert '-x c++-header' not in text
    assert load('join/receipt.json')['archive_compiler_commands'] == 0

def test_preserved_source_has_unattributed_sticky_fault_and_real_prefix_scope():
    wrapper = (DATA / 'inputs/ot_v41_rt_die_D1_scope.sv').read_text()
    bench = (DATA / 'inputs/tb_D1_scope_core.sv').read_text()
    assert 'if((|fault)||(|dbg_fs)||(|violations))$fatal(1,"D1_SOURCE_OR_LEDGER_FAULT")' in wrapper
    assert 'diag_cycle>=512' in bench
    review = load('review.json')
    assert review['claims']['original_PC24_cause'] == 'UNOBSERVED'
    assert review['claims']['full_token'] is False
    assert review['claims']['no_ECC_successor_selected'] is False

def test_all_committed_receipt_bytes_match_manifest():
    for path, expected in load('artifact_SHA256.json').items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
