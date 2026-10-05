"""Source and retained-log controls for additive producer accounting correction."""
import importlib.util
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import w17_window_epoch9_producer_log_reanalysis as analysis


@pytest.fixture(scope='module')
def result():
    return analysis.reanalyse()


def test_all_retained_events_and_checks_exact(result):
    assert result['original_verdict'] == 'FAIL_PRESERVED_NO_RETRY'
    for name in ('L0_no_retain','L0_retain'):
        c = result['cases'][name]
        assert c['events_identical'] and c['all_other_prediction_fields_identical']
        assert all(v['exact'] for v in c['comparison']['checks'].values())
        assert c['comparison']['mismatches'] == []


def test_bad_publication_edge_fails_both_modes(result):
    for name in ('L0_no_retain','L0_retain'):
        m = result['cases'][name]['controls']['next_edge_publication']
        assert [x['kind'] for x in m] == ['logical_publish']
        assert m[0]['predicted'][0][0] == m[0]['actual'][0][0]+1


def test_missing_ACT_fails_both_modes(result):
    for name in ('L0_no_retain','L0_retain'):
        m = result['cases'][name]['controls']['omitted_ACT']
        assert [x['kind'] for x in m] == ['per_PC']
        assert all(x[4] == 0 for x in m[0]['predicted'])
        assert all(x[4] > 0 for x in m[0]['actual'])


def source_texts():
    return [(ROOT/p).read_text() for p in (
        analysis.model.IDX,
        'rtl/test/w17_window_epoch9_candidate/ot_chip_v41x_window_kv_prefetch.sv',
        'rtl/test/w17_window_epoch9_producer/tb.sv')]


def test_source_ACT_omission_rejected():
    idx, pf, tb = source_texts()
    analysis.source_contract(idx,pf,tb)
    with pytest.raises(AssertionError):
        analysis.source_contract(idx.replace('st_act[p] = st_act[p] + 1;',''),pf,tb)


def test_source_publication_sampling_and_guard_mutants_rejected():
    idx, pf, tb = source_texts()
    for mutated in (tb.replace('logical_publish=mem.cyc;', 'logical_publish=mem.cyc+1;'),
                    tb.replace('#0.001;', ''),
                    tb.replace('acks==32&&logical_publish<0', 'acks==31&&logical_publish<0')):
        with pytest.raises(AssertionError):
            analysis.source_contract(idx,pf,mutated)
    with pytest.raises(AssertionError):
        analysis.source_contract(idx,pf.replace("if (bidx == 4'd15) row_valid[slot] <= 1'b1;", "row_valid[slot] <= 1'b1;"),tb)
