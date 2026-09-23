import hashlib
import json

import pytest

from tools import audit_hc1_referenced_designs as a

TECH, TI, LLAMA, QWEN, V41, INV, C, _ = a.load()
ENV = a.hc1_envelope(TECH, LLAMA)


def test_envelope_reproduces_the_published_token_rate_both_ways():
    # Throughput reading: every active Llama weight once per token at R.
    assert LLAMA['active_parameters'] / ENV['select_rate_cells_s'] == pytest.approx(1 / 16960)
    # Latency reading: 32 layers x 5 stages at the stage latency.
    assert 32 * a.LLAMA_STAGES_PER_LAYER * ENV['stage_latency_us'] == pytest.approx(1e6 / 16960)


def test_sram_bound_comes_from_the_published_transistor_count():
    assert ENV['sram_bytes_upper_bound_from_transistors'] == pytest.approx((53e9 - 8030261248) / 48)


def test_qwen_8k_kv_does_not_fit_an_hc1_die_but_2k_does():
    q = a.qwen_single_die(ENV, TI, C, QWEN, 'throughput')
    assert q['kv_fits_sram_upper_bound'] == {2048: True, 8192: False}
    assert 1 < q['capacity_ratio_to_hc1'] < 1.05


def test_v41_rom_die_count_holds_every_layer():
    r = a.rom_v41(ENV, TI, V41, INV, 0.25, 8192, 'throughput', 'spread')
    assert r['dies'] == 80 and r['max_die_fill'] <= 1


def test_concentrated_route_is_never_faster_than_spread():
    for reading in ('throughput', 'latency'):
        spread = a.rom_v41(ENV, TI, V41, INV, 0.5, 8192, reading, 'spread')['token_us']
        for route in ('concentrated_on_dense_die', 'concentrated_off_die'):
            assert a.rom_v41(ENV, TI, V41, INV, 0.5, 8192, reading, route)['token_us'] >= spread - 1e-9


def test_link_delay_monotonic_and_expert_cache_never_hurts_hbm():
    t = [a.rom_v41(ENV, TI, V41, INV, d, 8192, 'latency', 'spread')['token_us'] for d in a.LINK_DELAYS_US]
    assert t == sorted(t)
    miss = a.best_hbm(ENV, TI, C, V41, INV, 80, 0.25, 8192, 'throughput', 'all_miss')
    hit = a.best_hbm(ENV, TI, C, V41, INV, 80, 0.25, 8192, 'throughput', 'expected_hit')
    assert hit['token_us'] <= miss['token_us']


def test_hbm_refuses_arrays_that_cannot_cache_dense_weights():
    assert a.hbm_v41(ENV, TI, C, V41, INV, 2, 1, 0.25, 8192, 'throughput', 'all_miss') is None


def test_record_is_current():
    out = json.loads((a.ROOT / 'results/architecture/hc1_referenced_designs.json').read_text())
    for name, digest in out['input_sha256'].items():
        assert hashlib.sha256((a.ROOT / name).read_bytes()).hexdigest() == digest
