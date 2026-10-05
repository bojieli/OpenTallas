"""Source-model checks before any connected QE build."""
import json
from pathlib import Path
import sys
import re
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import w17_window_qdq8_connected_model as M

@pytest.fixture(scope='module')
def predictions():
    old=json.loads((M.PRODUCER_ROOT/'prediction.json').read_bytes())
    arith=json.loads((M.ARITH_ROOT/'model.json').read_bytes())
    return {n:M.replay(old['params'],n,arith['edge_calendar']) for n in (0,1)}


def test_before_fixture_prediction_identity(predictions):
    path=ROOT/'results/uarch/w17_window_qdq8_connected_prediction_20261002_before_fixture'
    for n,(summary,events) in predictions.items():assert summary==json.loads((path/('retain'+str(n)+'.json')).read_bytes())


def test_exact_one_QE_publication_and_32_write_intents(predictions):
    for summary,events in predictions.values():
        assert summary['QE_capture_cycles']==list(range(317,333))
        assert summary['QE_idle_sample']==335 and summary['producer_issue_cycle']==335
        blocks=[e for e in events if e['kind']=='block'];wr=[e for e in events if e['kind']=='request' and e['we']]
        assert len(blocks)==16 and blocks[0]['cycle']==336
        assert len(wr)==32
        for b in range(16):
            assert wr[b*2]['address']==262144+127*17+b and wr[b*2]['strobe']==0xffffffff
            assert wr[b*2+1]['address']==262144+127*17+16 and wr[b*2+1]['strobe']==1<<b


def test_natural_wrap_and_owners_never_alias(predictions):
    for summary,events in predictions.values():
        rd=[e for e in events if e['kind']=='request' and not e['we']]
        rows=[e for e in rd if e['sector']==0]
        assert [r['epoch'] for r in rows]==[(i+1)%512 for i in range(len(rows))]
        assert rows[511]['tag']==65536 and rows[512]['tag']==65568
        assert sum(r['epoch']==0 for r in rows)==1
        assert all((r['tag']&0xc000)==0 for r in rd)
        assert summary['final_epoch']==summary['cold_rows']%512


def test_per_PC_and_return_conservation(predictions):
    for summary,events in predictions.values():
        replies=[e for e in events if e['kind']=='reply']
        assert len(replies)==summary['read_requests']==17*summary['cold_rows']
        assert len({(e['op'],e['address'],e['tag']) for e in replies})==len(replies)
        assert len(summary['per_PC'])==32
        assert sum(p['writes'] for p in summary['per_PC'])==32
        assert all(p['reads']==summary['read_requests']//32 and p['q']==p['r']==0 for p in summary['per_PC'])
        assert all(p['activations']>0 for p in summary['per_PC'])


def test_scale_last_and_physical_visibility_from_WR_columns(predictions):
    for summary,events in predictions.values():
        seen={};due={}
        for e in sorted(events,key=lambda e:e.get('cycle',400001)):
            if e['kind']=='reply':seen.setdefault((e['op'],(e['address']-262144)//17),set()).add((e['address']-262144)%17)
            if e['kind']=='request' and not e['we'] and e['sector']==16:
                assert set(range(16))<=seen.get((e['op'],e['row']),set())
        columns=sorted([e for e in events if e['kind']=='column'],key=lambda e:(e['cycle'],e['pc']))
        for e in columns:
            if e['we']:due[e['address']]=e['tcol_ps']+7274
            elif e['address'] in due:assert e['tcol_ps']>=due[e['address']]
        assert summary['final_scale_visible_ps']==summary['last_WRcolumn_ps']+7274
        # The 13000ps lower bound is a source admission contract, never an injected wait.
        assert min(e['tcol_ps'] for e in columns if not e['we'])>=summary['last_WRcolumn_ps']+13000


def test_connected_fixture_direct_arithmetic_no_forced_epochs():
    tb=(ROOT/M.BENCH).read_text();body=(ROOT/M.BODY).read_bytes()
    assert '.kvb_v(cap_v)' in tb and '.cap_v(cap_v)' in tb
    assert 'cap_v=' not in tb and 'cap_codes=' not in tb and 'cap_scale=' not in tb
    assert not re.search(r'(?m)^\s*force\s+',tb)
    assert not re.search(r'refill_epoch\s*(?:<=|=(?!=))',tb)
    assert '.BL(16)' in tb and '.NBMAX(192)' in tb and '.CHUNK8(1)' in tb
    assert body==(ROOT/'rtl/test/w17_window_epoch9_producer/transport_body.svh').read_bytes()
    assert b'.LENW(4),.BEATW(4)' in body and b'.TAGW(17)' in body and b'.CLK_PS(1000)' in body
    assert 'q_expected_codes' not in tb[tb.index('ot_hdc_v41_qe #'):tb.index('ot_chip_v41x_window_block_guard')]
