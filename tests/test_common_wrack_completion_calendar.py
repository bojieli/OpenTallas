import importlib.util
from pathlib import Path
from fractions import Fraction
import pytest
s=importlib.util.spec_from_file_location('wrack_events',Path(__file__).resolve().parents[1]/'tools/common_wrack_completion_calendar.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def example():
    e=dict(stack=0,tag=0,sector=(1<<27)+1,epoch=42,completion_epoch=42,reserve_ps=0,column_ps=3000,visible_ps=11000,landing_accept_ps=15000,opcode_finish_ps=100000,result_visible_ps=110000,consumer_done_ps=120000)
    c=dict(stack=0,tag=0,sector=e['sector'],kind='write',bytes=32,issue_ps=3*m.FAST)
    return e,c

def test_final_event_not_eight_cycle_timer():
    e,c=example();r=m.completion_calendar([e],[c]);assert Fraction(r['timeline'][0]['credit_release_ps'])>120000
    assert Fraction(r['timeline'][0]['credit_release_ps'])>Fraction(r['timeline'][0]['landing_accept_ps'])+8*m.SLOW

def test_landing_does_not_complete_kernel():
    e,c=example();e['consumer_done_ps']=e['landing_accept_ps']
    with pytest.raises(ValueError):m.completion_calendar([e],[c])

def test_missing_stored_result_visibility_fails_closed():
    e,c=example();del e['result_visible_ps']
    with pytest.raises(ValueError):m.completion_calendar([e],[c])

def test_stale_completion_epoch_cannot_release_credit():
    e,c=example();e['completion_epoch']=41
    with pytest.raises(ValueError):m.completion_calendar([e],[c])

def test_four_credits_hold_until_reverse_completion():
    e,c=example();events=[];commands=[]
    for t in range(5):
        events.append(dict(e,tag=t,sector=e['sector']+t));commands.append(dict(c,tag=t,sector=e['sector']+t,issue_ps=(3+t)*m.FAST))
        events[-1]['column_ps']=10000;events[-1]['visible_ps']=18000;events[-1]['landing_accept_ps']=25000
    with pytest.raises(ValueError):m.completion_calendar(events,commands)

def test_read_and_write_share_single_command_port():
    e,c=example();read=dict(c,kind='read',bytes=32)
    with pytest.raises(ValueError):m.command_budget([read,c])

def test_RMW_requires_actual_read_and_merge_events():
    e,c=example();e['partial']=True
    with pytest.raises(ValueError):m.completion_calendar([e],[c])

def test_no_WR_visibility_from_acceptance():
    e,c=example();e['visible_ps']=3000
    with pytest.raises(ValueError):m.completion_calendar([e],[c])

def test_finite_byte_bucket_rejects_two_full_read_bursts():
    commands=[dict(stack=0,tag=i,kind='read',bytes=1024,issue_ps=(i+1)*m.FAST) for i in range(2)]
    with pytest.raises(ValueError):m.command_budget(commands)


def test_wrong_scheduled_sector_cannot_publish_completion():
    e,c=example();c['sector']+=1
    with pytest.raises(ValueError):m.completion_calendar([e],[c])
