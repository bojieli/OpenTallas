"""Static negative guards; reuse committed traces/logs, never build or run RTL."""
import copy
import importlib.util
import json
from pathlib import Path
import re

import pytest

ROOT=Path(__file__).resolve().parents[1]

def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'tools'/f'{name}.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod

GUARD=module('w17_window_epoch9_reproducible_prediction')
GATE=module('w17_window_epoch9_connected_gate')
OLD=ROOT/'results/uarch/w17_window_epoch9_timing_prediction_20261001_attempt1'
PRED=json.loads((OLD/'prediction.json').read_text())
EVENTS=[json.loads(x) for x in (OLD/'credit8_events.jsonl').read_text().splitlines()]
LOG=(ROOT/'results/rtl/w17_window_epoch9_connected_20261001_attempt2/runtime.log').read_text()


def test_committed_events_and_connected_returns_pass():
    for credits in (1,8):
        events=[json.loads(x) for x in (OLD/f'credit{credits}_events.jsonl').read_text().splitlines()]
        GUARD.check_event_contract(events,credits)
    assert not GATE.compare(LOG,PRED,EVENTS)['mismatches']


@pytest.mark.parametrize('credits',[0,2,16])
def test_unmodeled_credit_selection_rejected(credits):
    with pytest.raises(ValueError,match='Unsupported credits'):
        GUARD.check_event_contract(EVENTS,credits)


@pytest.mark.parametrize('mask',[1<<16,1<<14,1<<5])
def test_wrong_backend_owner_or_epoch_rejected(mask):
    events=copy.deepcopy(EVENTS);events[0]['tag']^=mask
    with pytest.raises(ValueError,match='Wrong owner/epoch/sector'):
        GUARD.check_event_contract(events,8)


def test_credit1_selection_cannot_use_credit8_trace():
    with pytest.raises(ValueError):GUARD.check_event_contract(EVENTS,1)


def test_ninth_outstanding_request_rejected():
    requests=[copy.deepcopy(e) for e in EVENTS if e['kind']=='request' and e['row']==0][:9]
    with pytest.raises(ValueError,match='Credit limit exceeded'):
        GUARD.check_event_contract(requests,8)


@pytest.mark.parametrize('mutation',['unissued','duplicate','scale_early'])
def test_invalid_return_or_publication_order_rejected(mutation):
    events=copy.deepcopy(EVENTS)
    index=next(i for i,e in enumerate(events) if e['kind']=='reply')
    if mutation=='unissued':events[0]['kind']='reply'
    elif mutation=='duplicate':events.insert(index+1,copy.deepcopy(events[index]))
    else:
        scale=next(e for e in events if e['kind']=='request' and e['sector']==16)
        events.insert(index,copy.deepcopy(scale))
    with pytest.raises(ValueError):GUARD.check_event_contract(events,8)


def test_original_prefetch_cannot_replace_qualified_candidate():
    path='rtl/test/w17_window_epoch9_candidate/ot_chip_v41x_window_kv_prefetch.sv'
    original=(ROOT/'rtl/chip/ot_chip_v41x_window_kv_prefetch.sv').read_bytes()
    with pytest.raises(ValueError,match='Source selection/hash mismatch'):
        GUARD.require_pins({path:PRED['candidate_added_sha256'][path]},lambda _:original)


def test_modified_pinned_owner_mux_rejected():
    path='rtl/chip/ot_chip_v41x_kv_rope_reqmux.sv'
    with pytest.raises(ValueError,match='Source selection/hash mismatch'):
        GUARD.require_pins({path:PRED['source_sha256'][path]},lambda p:(ROOT/p).read_bytes()+b'\n')


@pytest.mark.parametrize('mutation',['owner','credits','held_return_drop','stale_return'])
def test_connected_log_guard_rejects_corrupted_observation(mutation):
    log=LOG
    if mutation=='owner':
        log=re.sub(r'(BACKEND_REQUEST cycle=12302 pc=0 addr=40000 tag=)10020',r'\g<1>14020',log,count=1)
    elif mutation=='credits':log=log.replace('max_inflight=8','max_inflight=1')
    elif mutation=='held_return_drop':log=re.sub(r'BACKEND_REPLY[^\n]*\n','',log,count=1)
    else:log=re.sub(r'(CLIENT_REPLY cycle=12355 tag=)20',r'\g<1>40',log,count=1)
    assert log!=LOG
    assert GATE.compare(log,PRED,EVENTS)['mismatches']
