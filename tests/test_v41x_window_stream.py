"""Matched finite-credit replay evidence; numeric engine integration is separate."""
import json
from tools.rtl_v41x_window_stream_gate import OUT, hashes


def test_window_stream_record_current():
    record = json.loads(OUT.read_text())
    assert record['status'] == 'pass'
    assert record['sources'] == hashes()
    assert record['credit_slots'] == 4
    assert record['fifo_data_bytes'] == 8448
    assert 'max_reserved=4' in record['edges']
    assert 'longstall=23' in record['edges']


def test_same_producer_and_completion_contract():
    record = json.loads(OUT.read_text())
    for arm in ('baseline', 'ii1'):
        for scenario in record[arm]:
            assert scenario['metrics']['accepted'] == 64
            assert scenario['metrics']['descriptors'] == 2
            assert scenario['metrics']['max_outstanding'] == 1
    assert record['baseline'][0]['replays'][0]['min_gap'] == 4
    assert record['ii1'][0]['replays'][0]['min_gap'] == 1
