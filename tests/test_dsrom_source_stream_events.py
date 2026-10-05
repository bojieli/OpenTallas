import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_source_stream_events as T


def matrix(fmt, K, count=1):
    words = T.C.S.seg_words(fmt, 0, K)
    u0, u1 = T.C.S.unit_range(fmt, 0, K)
    issue = 8*sum(max(8, (min(8, u1-start)+3)//4 if fmt == 'bf16' else min(8, u1-start),
                      count*sum(len(T.C.S.unit_halves(fmt, 0, K, u)) for u in range(start, min(u1, start+8))))
                  for start in range(u0, u1, 8))
    return dict(format=fmt, K=K, segments=[[0,K]], plans=[[0,0,0,count,128,0,words]],
                issue_cycles_LAT8_condition=issue)


def test_fp8_decode_and_loading_threshold():
    rounds, beats = T.stream(matrix('fp8', 5120))
    assert len(beats) == 192
    assert [r['cycles_per_block'] for r in rounds] == [16,8]
    for beat in beats:
        word = beat['word48']
        if word & 1:
            unit = word >> 1 & 255
            block = word >> 9 & 7
            half = 1 if word >> 12 & 2 else 0
            assert beat['required_loaded_elements'] == unit*512+half*256+(block+1)*32
            assert beat['units'] == [unit]


def test_bf16_group_decoding_and_order():
    _, beats = T.stream(matrix('bf16', 1024))
    for block in range(8):
        valid = [b for b in beats if b['block'] == block and b['word48'] & 1]
        assert [u for b in valid for u in b['units']] == list(range(8))
        for b in valid:
            word = b['word48']
            decoded = [word >> (8+8*i) & 255 for i in range(4) if word >> (4+i) & 1]
            assert decoded == b['units']
            assert b['required_loaded_elements'] == (max(decoded)+1)*128


def test_resident_row_replication_charges_read_service():
    _, single = T.stream(matrix('fp4', 4096, 1))
    _, replicated = T.stream(matrix('fp4', 4096, 4))
    assert len(replicated) == 4*len(single)
    assert sum(bool(b['word48'] & 1) for b in replicated) == sum(bool(b['word48'] & 1) for b in single)


def test_stale_owner_issue_count_is_rejected():
    m = matrix('fp8',5120)
    m['issue_cycles_LAT8_condition'] -= 1
    with pytest.raises(ValueError, match='stream length'):
        T.stream(m)
