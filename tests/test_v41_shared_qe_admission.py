import json
from pathlib import Path
import pytest
from tools.v41_shared_qe_admission import analyze
ROOT=Path(__file__).resolve().parents[1]

def test_recorded_operating_point_rejected():
    record=json.loads((ROOT/'results/rtl/v41_shared_qe_admission.json').read_text())
    for arm in ('alone','mixed'):
        got=analyze(ROOT/f'results/rtl/v41_shared_qe_admission/{arm}.csv',3840)
        assert got==record[arm]
        assert not got['fixed_rate_window_pass']
        assert got['words_already_resident_at_that_start']>1024

def test_prefetched_fast_service_and_missing_word(tmp_path):
    p=tmp_path/'trace.csv';p.write_text('0,1\n1,2\n2,3\n3,4\n')
    assert analyze(p,4,2)['fixed_rate_window_pass']
    p.write_text('0,1\n1,2\n1,3\n3,4\n')
    with pytest.raises(ValueError):analyze(p,4,2)
