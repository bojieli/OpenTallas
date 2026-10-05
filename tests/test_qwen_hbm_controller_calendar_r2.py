"""Pinned bank/address metadata and finite service, no RTL/payload execution."""
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from qwen_hbm_controller_calendar_r2 import (BankCalendar,LoadedStack,SharedDie,Beat,
    bankmap,edge,crossed,kv_rows,kv_read_rows,weight_ranges,fixture,audit_bank_events,
    PROGRAM,BASE,REV,SOURCE,R1,source_timing,pinned,DIR)

@pytest.fixture(scope='module')
def graph():return json.loads(pinned(ROOT,BASE,PROGRAM))

@pytest.fixture(scope='module')
def timing():return source_timing()

def test_source_bankmap_and_full_address(timing):
    raw=pinned(ROOT,REV,SOURCE)
    for part in (b'2 + LPC + 5 + 3',b'(s >> (2 + 2 * LPC))',b'((s ^ row) & 3)',
                 b'last_act_bg[p][bg] + RRDL_PS',b'faw[p][0] + FAW_PS'):
        assert part in raw
    assert bankmap(0)==dict(pc=0,bank=0,bg=0,row=0)
    assert bankmap(1)==dict(pc=0,bank=1,bg=1,row=0)
    assert bankmap(1<<32)['row']==1<<17
    with pytest.raises(ValueError):bankmap(1<<34)
    with pytest.raises(ValueError):edge(0,0)

def test_actual_all144_WR_demand_hashes_and_prefix_read(graph):
    adapter=json.loads(pinned(ROOT,BASE,DIR+'finite_service_adapter_r2.json'))
    for d in adapter['writer_demands']:
        rows=kv_rows(graph,graph['instructions'][d['writer']],d['position'])
        assert hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()==d['sector_descriptor_sha256']
        assert len(rows)==272 and sum(r['partial'] for r in rows)==256
    reads=kv_read_rows(graph,graph['instructions'][10],1)
    assert len(reads)==288
    assert sum(r['mask'].bit_count() for r in reads)==2048
    assert len(kv_read_rows(graph,graph['instructions'][10],0))==272

def test_weight_ranges_are_actual_program_not_phases(graph):
    weights=weight_ranges(graph)
    assert len(weights)==290
    assert all(len(w['ranges'])==2 for w in weights)
    target=next(w for w in weights if w['weight']=='L0.o.d0')
    assert target['instruction']==17
    assert target['dependencies']==[16]
    assert graph['instructions'][16]['dependencies']==[14,15]
    assert graph['instructions'][15]['dependencies']==[12,14]
    assert all(w['phase_provider'].startswith('MISSING') for w in weights)

def test_causal_ACT_and_source_backdate_difference(timing):
    b=Beat(0,1,1<<48,1)
    causal=BankCalendar(timing,1000);literal=BankCalendar(timing,1000)
    assert causal.estimate(b,18000)==29375  # source estimate, not final legal issue
    assert causal.plan(b,18000)==38000
    assert literal.plan(b,18000,causal=False)==30000
    assert causal.events[0]['ps']==18000 and literal.events[0]['ps']==10000
    assert audit_bank_events(causal.events,timing)['status'].startswith('PASS')

def test_refresh_now_catchup_and_multiple_RFC(timing):
    b=Beat(0,1,1<<48,1)
    literal=BankCalendar(timing,1000);literal.plan(b,4000000,causal=False)
    assert not any(e['kind']=='REF' for e in literal.events)
    causal=BankCalendar(timing,1000);column=causal.plan(b,12000000)
    refs=[e['ps'] for e in causal.events if e['kind']=='REF']
    assert len(refs)==3
    assert all(y-x>=timing['RFC_PS'] for x,y in zip(refs,refs[1:]))
    assert column>=refs[-1]+timing['RFC_PS']+timing['RCDRD_PS']
    audit_bank_events(causal.events,timing)

def test_turnarounds_bank_groups_and_PRE_recovery(timing):
    bank=BankCalendar(timing,1000)
    rd=bank.plan(Beat(0,1,1,1),18000)
    wr=bank.plan(Beat(1,2,1,1,write=True),rd)
    assert wr-rd>=timing['RTW_PS']
    other=bank.plan(Beat(0,3,1,1),wr)
    assert other-wr>=timing['CWL_PS']+timing['BURST_PS']+timing['WTRS_PS']
    same=bank.plan(Beat(1,4,1,1),other)
    assert same-wr>=timing['CWL_PS']+timing['BURST_PS']+timing['WTRL_PS']
    # A second row in same PC/bank must PRE, wait RP and tRC, then ACT.
    addr=next(s for s in range(32768,65536) if bankmap(s)['pc']==0 and bankmap(s)['bank']==0)
    bank.plan(Beat(addr,5,1,1),same)
    assert any(e['kind']=='PRE' for e in bank.events)
    audit_bank_events(bank.events,timing)

def test_independent_legality_checker_rejects_early_column(timing):
    bank=BankCalendar(timing,1000);bank.plan(Beat(0,1,1,1),18000)
    bad=[dict(e) for e in bank.events];bad[-1]['ps']=18001
    with pytest.raises(AssertionError):audit_bank_events(bad,timing)

def test_pending_capacity_before_bank_mutation(timing):
    stack=LoadedStack(timing,1000,2000)
    stack.add(0,'write');stack.c.accept(Beat(0,0,1,1,write=True),0)
    stack.tasks=[];stack.phase[0]='reserve'
    for p in (1,2,3,4):stack.reserved_WR[p]=Beat(p,100+p,1,1,write=True)
    head=stack.c.q[0][0]
    stack.step(Fraction(0))
    assert stack.phase[0]=='reserve' and stack.c.q[0][0]==head
    assert not stack.bank.events and not stack.c.pending

def test_return_prefetch_has_samePC_bubble(timing):
    stack=LoadedStack(timing,1000,2000)
    for i in range(2):
        stack.add(0,'KV_read');stack.c.accept(Beat(0,i,1,1),0);stack.c.column(0,0)
    stack.tasks=[]
    stack.step(Fraction(30000));assert len(stack.c.r[0])==1
    stack.step(Fraction(31000));assert len(stack.c.r[0])==1
    stack.step(Fraction(32000));assert not stack.c.r[0]
    assert stack.read_prefetch_waits==1

def test_explicit_periods_and_max_lease(graph):
    # Actual address fixture but conditional phases, never hardware timing.
    x=fixture(graph,competing_weights=True)
    assert x['shared_sector_credit_peak']<=4 and x['shared_ACK_record_peak']<=4
    assert sum(s['kind_counts']['write'] for s in x['writer_stacks'])==272
    assert sum(s['kind_counts']['RMW_read'] for s in x['writer_stacks'])==256
    assert sum(s['kind_counts']['weight_prefetch_fixture'] for s in x['writer_stacks'])==64
    assert sum(s['kind_counts']['KV_read'] for s in x['loaded_stacks'])==288
    assert all(s['peak_pending_WR_slots']<=4 and s['peak_PC_request_depth']<=64 and s['peak_PC_return_depth']<=32 for s in x['loaded_stacks'])
    assert all(s['status'].startswith('PASS') for s in x['calendar_legal'])
    assert Fraction(x['lease_release_max_ps'])==max(Fraction(x['synthetic_scores_done_ps']),Fraction(x['synthetic_PV_done_ps']))
    assert Fraction(x['synthetic_PV_done_ps'])>Fraction(x['synthetic_EXP_SUM_done_ps'])>Fraction(x['synthetic_scores_done_ps'])
    assert not x['hardware_build_ready'] and x['rate_credit']==0
    for stack in x['addressed_timeline']:
        events={}
        for e in stack['events']:events.setdefault(e['tag'],{})[e['event']]=Fraction(e['ps'])
        for times in events.values():
            if 'WR_column' in times:
                assert times['WR_capacity_reserved']<=times['WR_column']
                assert times['WR_backing_visible']>=times['WR_column']+7274
                assert times['WR_visible_ACK_accept']>=times['WR_column']+7274+10000
                assert times['reverse_credit']>=times['ACK_retire']
    assert edge(1234,Fraction(2500,3))==Fraction(5000,3)
    assert crossed(1234,2000)==6000

def test_r1_byte_identical():
    for p in ('tools/qwen_hbm_controller_events_r1.py','tests/test_qwen_hbm_controller_events_r1.py',
              'results/uarch/qwen_hbm_controller_events_20261001/model_r1.json',
              'results/uarch/qwen_hbm_controller_events_20261001/review_r1.json',
              'results/uarch/qwen_hbm_controller_events_20261001/fixture_failure_r1.json'):
        assert (ROOT/p).read_bytes()==pinned(ROOT,R1,p)


def test_FAW_RRDL_and_explicit_nonuniversal_clock(timing):
    b=BankCalendar(timing,1000)
    # Source map supplies four BGs; further banks force new ACTs.
    targets=[]
    for addr in range(32768):
        m=bankmap(addr)
        if m['pc']==0 and m['bank'] not in [bankmap(a)['bank'] for a in targets]:
            targets.append(addr)
        if len(targets)==6:break
    now=18000
    for i,addr in enumerate(targets):
        now=b.plan(Beat(addr,i,1,1,write=True),now)
    audit_bank_events(b.events,timing)
    assert len([e for e in b.events if e['kind']=='ACT'])==6
    c=BankCalendar(timing,Fraction(2500,3))
    assert c.plan(Beat(0,1,1,1),18000)!=BankCalendar(timing,1000).plan(Beat(0,1,1,1),18000)


def test_actual_address_phase_provider_nonuniqueness(graph,timing):
    addr=kv_rows(graph,graph['instructions'][10],1)[0]['sector']
    columns=[]
    for accept in (0,50000):
        bank=BankCalendar(timing,1000)
        columns.append(bank.plan(Beat(addr,1,1<<48,1,accepted_ps=accept),accept+18000))
        audit_bank_events(bank.events,timing)
    assert columns[1]-columns[0]==50000
