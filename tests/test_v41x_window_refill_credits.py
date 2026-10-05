import json
from tools.rtl_v41x_window_refill_credits_gate import OUT, hashes


def test_refill_credits_record_current():
    r = json.loads(OUT.read_text())
    assert r['status'] == 'pass'
    assert r['sources'] == hashes()
    assert r['contract']['new_payload_buffer_bytes'] == 0
    assert r['contract']['stage_write_ports'] == 1
    assert r['contract']['extra_state_bits'] == 55
    assert set(r['fault_cases']) == {'STALE_EPOCH', 'UNKNOWN_SECTOR', 'POISON', 'DUPLICATE'}


def test_matched_service_and_bounded_credits():
    r = json.loads(OUT.read_text())
    for a,b in zip(r['cases'][:4],r['cases'][4:]):
        assert (a['latency'],a['queue_limit']) == (b['latency'],b['queue_limit'])
        assert a['credits'] == 1 and b['credits'] == 8
        for x in (a,b):
            assert x['metrics']['max_outstanding'] <= min(x['credits'],x['queue_limit'])
            assert x['result']['rows'] == 256
            assert x['metrics']['reads'] == 4352
            assert x['metrics']['writes'] == 4096
            assert x['metrics']['accepted'] == 64
        assert b['result']['refill0'] < a['result']['refill0']
