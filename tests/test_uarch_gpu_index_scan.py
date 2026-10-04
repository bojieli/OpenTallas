"""GPU comparator uses the canonical eight source-owned index reads, not38."""
import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import uarch_model as u


def test_exact_sources_ratios_KV_homes_and_candidate_bound():
    r = u.v41_gpu_index_scan(1048576)
    assert r['scanning_layers'] == [2, 8, 14, 20, 24, 28, 32, 36]
    assert [x['compression_ratio'] for x in r['per_layer']] == [2, 2, 2, 1, 1, 1, 1, 1]
    assert [x['KV_source_layer'] for x in r['per_layer']] == [2, 8, 14, 20, 20, 20, 20, 20]
    assert r['entries'] == 2686976 and r['bytes'] == 182714368
    assert 1048576 * 38 * 68 / r['bytes'] == pytest.approx(14.829268292682928)


def test_literal_full_score_golden_sensitivity_not_candidate_gather_claim():
    r = u.v41_gpu_index_scan(1048576, candidate_gather=False)
    assert r['entries'] == 6815744 and r['bytes'] == 463470592
    assert [x['entries'] for x in r['per_layer'][3:]] == [1048576] * 5
    assert r['candidate_gather'] is False


def test_eight_scans_and_full_score_sensitivity_match_actual_native_program():
    program = json.loads((ROOT / 'results/rtl/w19_hbm_tp96_program_oreduce.json').read_text())
    actual = [(layer['layer'], op['src'], op['n']) for layer in program['layers']
              for op in layer['ops'] if op.get('fn') == 'index_scores']
    priced = u.v41_gpu_index_scan(program['position'] + 1, candidate_gather=False)
    assert actual == [(row['layer'], row['KV_source_layer'], row['entries']) for row in priced['per_layer']]


@pytest.mark.parametrize('ctx', [1, 3, 8192, 32769, 200000, 1048576])
def test_bytes_match_same_ROM_operator_inventory_at_exact_context(ctx):
    c = u.A._env()['c']
    expected = sum(op['bytes']['idx'] for L in range(c['num_layers'])
                   for op in u.A.ops_of_layer(c, L, ctx)[0])
    assert u.v41_gpu_index_scan(ctx)['bytes'] == expected
    if ctx <= 16384:
        assert expected == u.v41_gpu_index_scan(ctx, candidate_gather=False)['bytes']


@pytest.mark.parametrize('change', [
    lambda c: c['modes'][3].update(scans_index=True),
    lambda c: c['modes'][2].update(scans_index=False),
    lambda c: c['compress_ratios'].__setitem__(2, 4),
    lambda c: c['kv_source_layer_ids'].append(24),
    lambda c: c['modes'][2].update(index_scan_entries_cap=16384),
    lambda c: c['modes'][24].update(index_scan_entries_cap=512),
    lambda c: c.update(candidate_source_layer_id=24),
])
def test_source_or_cap_mutations_refused(change):
    c = copy.deepcopy(u.A._env()['c']); change(c)
    with pytest.raises(ValueError):
        u.v41_gpu_index_scan(1048576, c=c)


@pytest.mark.parametrize('ctx', [0, -1, 1.5, True])
def test_invalid_context_refused(ctx):
    with pytest.raises(ValueError):
        u.v41_gpu_index_scan(ctx)


def test_all_three_GPU_pricers_use_one_source_inventory(monkeypatch):
    # the index-scan correction is compared at the superseded 8 us all-reduce it was recorded under (the default is
    # now the measured H100 fenced one-shot, results/uarch/hbm_switch_latency_authoritative_20261004)
    monkeypatch.setattr(u, 'NCCL_ALLREDUCE_S', u.NCCL_ALLREDUCE_ASSUMED_SUPERSEDED_S)
    scan = u.v41_gpu_index_scan(1048576)
    tier = u.gpu_tier2()[1]
    econ = u.gpu_economics()['v41']
    assert tier['index_scan'] == econ['index_scan'] == scan
    assert econ['tokens_s_b1'] == round(1 / u.gpu_tier2_v41_ctx(1048576), 1)
    assert tier['tokens_s'] > 277.7
    assert u.gpu_tier2_v41_ctx(1048576, candidate_gather=False) > u.gpu_tier2_v41_ctx(1048576)


def test_current_repricing_record_matches_sources_and_retains_old_results():
    r = json.loads((ROOT / 'results/uarch/dsrom_gpu_index_scan_correction_20261003/model.json').read_text())
    for source, pin in r['source_sha256'].items():
        assert hashlib.sha256((ROOT / source).read_bytes()).hexdigest() == pin
    assert r['unchanged_wire_result_sha256'] == hashlib.sha256(
        (ROOT / 'results/uarch/dsrom_hub_edge_wires_20261003/model.json').read_bytes()).hexdigest()
    assert r['before']['tier2'][1]['tokens_s'] == 277.7
    assert r['after']['tier2'][1]['tokens_s'] == u.gpu_tier2()[1]['tokens_s']
