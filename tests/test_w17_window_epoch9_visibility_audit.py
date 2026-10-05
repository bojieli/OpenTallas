"""No build: analytic visibility bounds, exact prepared calendar and pin checks."""
import importlib.util
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'results/uarch/w17_window_epoch9_producer_prediction_20261001_attempt2'
MODEL=json.loads((P/'prediction.json').read_text())


def test_every_WR_phase_first_possible_READ_is_visible():
    # Registered ack A=ceil(WR/1000)+1; waiting descriptor can prefetch A+1,
    # source grant A+2 and backend REQ delay10cycles. Not a frequency proof.
    for phase in range(1000):
        wr=100000+phase;ack=(wr+999)//1000+1
        first_read=(ack+2)*1000+10000
        assert first_read-wr>=13000
        assert first_read>=wr+7274


def test_scale_barrier_minimum_without_constant_fit():
    # Source issue capacity one/cycle, credits8. Every beat response takes at
    # least ceil(REQ+CL+BURST+RSP)/CLK=34cycles, irrespective bank/refresh stalls.
    pending=[];grants=[];returns=[]
    for c in range(200):
        pre=len(pending)
        if len(grants)<16 and pre<8:
            grants.append(c);pending.append(c+34)
        reply=next((v for v in pending if v<=c),None)
        if reply is not None:pending.remove(reply);returns.append(c)
        if len(returns)==16:break
    assert grants[15]==42 and returns[-1]==76
    scale_grant=returns[-1]+1
    # Earliestfirstgrant relative WR is3cycles; plusREQ10cycles.
    assert (3+grants[15]+10)*1000==55000
    assert (3+scale_grant+10)*1000==90000


def test_exact_source_COUNT1_calendar_and_L0_scope():
    a=MODEL['cases']['source_COUNT1_boundary'];columns=a['first_own_row_READcolumns']
    assert a['final_scale_visible_ps']==1111274
    assert [columns[s]['tcol_ps'] for s in ('0','15','16')]==[1118000,1389628,1425000]
    assert columns['0']['tcol_ps']-a['final_scale_visible_ps']==6726
    assert 'Not a legal actualL0' in MODEL['visibility_contract']['COUNT1']


def test_all_own_row_columns_after_visible_and_32_masks():
    for name in MODEL['cases']:
        events=[json.loads(x) for x in (P/(name+'_events.jsonl')).read_text().splitlines()]
        wr=[e for e in events if e['kind']=='request' and e['we']]
        assert len(wr)==32
        for i,e in enumerate(wr):
            assert e['address']==262144+127*17+(i//2 if i%2==0 else 16)
            assert e['strobe']==(0xffffffff if i%2==0 else 1<<(i//2))
            assert 0<=e['address']<264320
        visible={}
        for e in events:
            if e['kind']=='write_visible':visible[e['address']]=e['ps']
        for e in events:
            if e['kind']=='column' and not e['we'] and e['address'] in visible:
                assert e['tcol_ps']>=visible[e['address']]


def test_no_forced_epoch_or_visibility_guard_in_fixture():
    text=(ROOT/'rtl/test/w17_window_epoch9_producer/tb.sv').read_text()
    assert 'ot_hdc_v41x_window_kv_blocks' in text and 'ot_chip_v41x_window_block_guard' in text
    assert 'ot_chip_v41x_attn_desc_lifecycle' in text
    assert not re.search(r'(?<![\w-])force\s|\.refill_epoch\s*=(?!=)',text)
    assert 'WRITE_VISIBILITY_GUARD' not in text
    assert '.prime_v(prime_v)' in text and 'primed<127' in text
    assert 'latest_visible_ps' in text and 'column_ps[p]<latest_visible_ps[sec]' in text
