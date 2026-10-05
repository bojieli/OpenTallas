"""Source/preparation validation only. No simulator/compiler is launched."""
import hashlib
from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from qwen_hbm_provider_prep_r3 import (observed_source,strip_observer,plan,stimulus,
    stimulus_header,audit_journal,audit_reservation_projection,prepare_sources,read_journal,REV,SOURCE,pinned,source_timing,FIXTURE)

def event(kind,logical=30000,observed=30000,tag=1,beat=0):
    return dict(kind=kind,sim_ps=observed+6000,observe_ps=observed,logical_ps=logical,
        pc=0,bank=0,row=0,sector=0,tag=tag,beat=beat,arrival_ps=0,q_n=1,r_n=0)

def test_observer_is_reversible_actual_pin_and_has_no_dut_writes():
    raw=pinned(ROOT,REV,SOURCE);text,hooks=observed_source(raw)
    assert strip_observer(text).encode()==raw
    assert len(hooks)==14
    assert 'ACT_RESERVATION' in text and 'WR_VISIBLE' not in text
    assert '$realtime*1000.0' in text
    assert 'qhp_log("BACKING_STORE",now,now' in text
    assert text.count('// QHP_BEGIN')==text.count('// QHP_END')==14

def test_changed_source_anchor_refuses_observation():
    raw=pinned(ROOT,REV,SOURCE).replace(b'schedule = tcol;',b'schedule = different;')
    with pytest.raises(ValueError):observed_source(raw)

def test_literal_source_is_calendar_not_command_emitter():
    raw=pinned(ROOT,REV,SOURCE)
    assert b'simulation only' in raw
    port_header=raw.split(b') (',1)[1].split(b');',1)[0]
    assert b'rsp_v' in port_header
    for name in (b'act_valid',b'pre_valid',b'ref_valid',b'wr_visible',b'wr_done',b'epoch'):
        assert name not in port_header
    assert b'while (next_ref[p] <= max2(tmin, last_col[p]))' in raw
    assert b'mem[q_addr[p][slot] % MEM_WORDS] = q_data[p][slot]' in raw

def test_literal_past_ACT_and_refresh_witness_not_r2_transfer():
    x=plan();e=x['source_equation_counterexample']
    assert e['inactive_bank_ACT_logical_ps']==44000
    assert e['inactive_bank_ACT_logical_ps']<e['schedule_call_ps']
    assert not e['source_refresh_loop_runs']
    assert x['source_classification']=='SIMULATION_ARCHITECTURAL_CALENDAR_ABSTRACTION'
    assert not x['RTL_compiled'] and not x['compile_GO']

def test_actual_stimulus_addresses_and_finite_bench_source():
    s=stimulus();header=stimulus_header(s)
    assert len(s['WR_rows'])==4 and all(r['partial'] for r in s['WR_rows'])
    assert header.count('QHP_KV')==4
    assert (ROOT/'tools/fixtures/qwen_hbm_provider_r3/stimulus_r3.svh').read_text()==header
    raw=(ROOT/FIXTURE).read_text()
    for token in ('.NPC(NPC)', '.AW(AW)', '.QD(64)', '.RQD(32)', '.MEM_WORDS(4096)',
        'SOURCE_TRACE_COMPLETE_NOT_WR_PROVIDER_DONE','dut.cyc<4100','live_reads[grant_client]>34','prev_held','34\'d1<<32'):
        assert token in raw
    assert 'wr_accepted-=1' not in raw

def test_journal_due_identity_positive_and_mutants():
    t=source_timing();tail=t['CL_PS']+t['BURST_PS']+t['RSP_PS']
    source=[event('ENQUEUE',0,0),event('RD_COLUMN_RESERVATION',30000,0),
            event('RETURN_ENQUEUE',30000+tail,30000),event('READ_TAKE',30000+tail,54000)]
    assert not audit_journal(source,t)['findings']
    early=list(source);early[-1]=event('READ_TAKE',30000+tail,53000)
    assert any(f['rule']=='read_identity_due' for f in audit_journal(early,t)['findings'])
    bad=list(source);bad[2]=event('RETURN_ENQUEUE',30000+tail-1,30000)
    assert any(f['rule']=='read_due_equation' for f in audit_journal(bad,t)['findings'])
    wrong=list(source);wrong[-1]=event('READ_TAKE',30000+tail,54000,tag=2)
    assert audit_journal(wrong,t)['findings']
    assert audit_journal(source+[source[-1]],t)['findings']

def test_ACT_causality_and_baseline_WR_visibility_are_failures():
    t=source_timing()
    act=audit_journal([event('ACT_RESERVATION',44000,4100000)],t)
    assert act['findings'][0]['verdict']=='FAIL_AS_EMITTED_COMMAND'
    wr=[event('WR_COLUMN_RESERVATION',20000,0),event('WR_POP',20000,20000),event('BACKING_STORE',20000,20000)]
    result=audit_journal(wr,t)
    assert result['findings'][0]['rule']=='column_to_backing_visibility'
    assert result['findings'][0]['earliest_visible_ps']==27274
    assert result['findings'][0]['verdict']=='FAIL_AS_WR_VISIBLE_PROVIDER'
    assert not result['WR_visible_hook_present']

def test_parser_and_schema(tmp_path):
    keys=['kind','sim_ps','observe_ps','logical_ps','pc','bank','row','sector','tag','beat','arrival_ps','q_n','r_n']
    e=event('ACT_RESERVATION');p=tmp_path/'journal.tsv'
    p.write_text('|'.join(keys)+'\n'+'|'.join(str(e[k]) for k in keys)+'\n')
    assert read_journal(p)==[e]
    p.write_text('wrong\n')
    with pytest.raises(ValueError):read_journal(p)


def test_source_projection_checks_tRCD_mutant():
    t=source_timing()
    events=[event('ACT_RESERVATION',10000,0),event('RD_COLUMN_RESERVATION',30000,0)]
    assert audit_reservation_projection(events,t)['status'].startswith('PASS')
    events[1]=event('RD_COLUMN_RESERVATION',29000,0)
    with pytest.raises(AssertionError):audit_reservation_projection(events,t)

def test_accept_expand_and_reorder_identity_mutants():
    accept=event('ACCEPT_RD',0,0,beat=1);enqueue=event('ENQUEUE_RD',0,0)
    reorder=event('REORDER',1000,1000)
    good=[accept,enqueue,reorder]
    assert not audit_journal(good,source_timing())['findings']
    wrong=dict(reorder,sector=1)
    assert any(f['rule']=='queue_reorder_origin' for f in audit_journal([accept,enqueue,wrong],source_timing())['findings'])
    assert any(f['rule']=='accept_to_beat_identity' for f in audit_journal([enqueue],source_timing())['findings'])

def test_materialized_review_sources_no_compile(tmp_path):
    target=tmp_path/'source-only'
    checksums=prepare_sources(target)
    assert len(checksums)==3
    raw=pinned(ROOT,REV,SOURCE)
    assert strip_observer((target/'controller_observed.sv').read_text()).encode()==raw
    assert (target/'tb_actual_controller.sv').read_bytes()==(ROOT/FIXTURE).read_bytes()
    with pytest.raises(FileExistsError):prepare_sources(target)

def test_projection_turnaround_mutants():
    from qwen_hbm_controller_calendar_r2 import bankmap
    t=source_timing()
    def mapped(kind,sector,time):
        m=bankmap(sector)
        return dict(event(kind,time,0),sector=sector,pc=m['pc'],bank=m['bank'],row=m['row'])
    good=[mapped('ACT_RESERVATION',0,10000),mapped('ACT_RESERVATION',1,20000),
          mapped('RD_COLUMN_RESERVATION',0,30000),mapped('WR_COLUMN_RESERVATION',1,41000),
          mapped('RD_COLUMN_RESERVATION',0,54000)]
    audit_reservation_projection(good,t)
    bad=list(good);bad[3]=mapped('WR_COLUMN_RESERVATION',1,39947)
    with pytest.raises(AssertionError):audit_reservation_projection(bad,t)
    bad=list(good);bad[4]=mapped('RD_COLUMN_RESERVATION',0,52000)
    with pytest.raises(AssertionError):audit_reservation_projection(bad,t)

def test_projection_refresh_and_FAW_mutants():
    from qwen_hbm_controller_calendar_r2 import bankmap
    t=source_timing()
    good=[event('ACT_RESERVATION',10000,0),event('RD_COLUMN_RESERVATION',30000,0),
          event('PREALL_RESERVATION',50000,0),event('REF_RESERVATION',66250,0),
          event('ACT_RESERVATION',500000,0),event('RD_COLUMN_RESERVATION',520000,0)]
    for e in good:
        if e['kind'] in ('PREALL_RESERVATION','REF_RESERVATION'):e['bank']=-1
    audit_reservation_projection(good,t)
    bad=list(good);bad[4]=event('ACT_RESERVATION',416249,0)
    with pytest.raises(AssertionError):audit_reservation_projection(bad,t)
    acts=[]
    for sector,time in zip((0,1,2,3,4224),(10000,12500,15000,17500,25000)):
        m=bankmap(sector)
        acts.append(dict(event('ACT_RESERVATION',time,0),sector=sector,bank=m['bank'],row=m['row']))
    audit_reservation_projection(acts,t)
    bad=list(acts);bad[4]=dict(acts[4],logical_ps=22500)
    with pytest.raises(AssertionError):audit_reservation_projection(bad,t)
