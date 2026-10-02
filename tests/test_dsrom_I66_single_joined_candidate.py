import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import dsrom_I66_single_joined_candidate as J
import dsrom_I66_visibility_anchored_calendar as V


def header(user):
    return dict(generation=7, operation_sequence=9, owner_stage=1, packet_kind=2,
                packet_ordinal=3, payload_bits=576*63, rank=2, user=user)


@pytest.mark.parametrize('user',[0,1,65535,65536,2**31,2**32-1])
def test_full_user32_injective_roundtrip(user):
    assert J.decode_header(J.encode_header(header(user))) == header(user)
    assert J.encode_header(header(user)) != J.encode_header(header(user ^ 65536))


@pytest.mark.parametrize('user',[-1,2**32,True,1.0])
def test_invalid_identity_rejected(user):
    with pytest.raises(ValueError): J.encode_header(header(user))


def args():
    ctx=dict(stage=0, rank=0, expert=0, phase=10, key_word=2149580800,
             generation=7, user=2**32-1, xversion=52, pc=66)
    return dict(ctx=ctx,rows={r:(r%256)//2 for r in range(576)},raw={r:r for r in range(576)},
                capacity=1,issue_edges=[30*r for r in range(576)],return_delays={0:9,1:12},
                consumer_edges=[30*r+16 for r in range(576)],visible_edges={r:30*r+20 for r in range(576)},
                ack_edge=30*576,credit_return_delay=7)


def test_source_debt_retained_to_visibility_plus_positive_feedback():
    a=args();m=V.replay(**a)
    assert m['rows']==576
    visible={e['row']:int(e['time']) for e in m['journal'] if e['kind']=='home_visible'}
    credit=[e for e in m['journal'] if e['kind']=='credit_return_capture']
    assert all(int(e['time'])==visible[e['row']]+7 for e in credit)
    assert not m['physical_admission']


def test_same_edge_credit_cannot_fund_next_issue():
    a=args();a['issue_edges'][1]=27
    with pytest.raises(ValueError): V.replay(**a)


def test_refused_consumer_does_not_retire_credit():
    a=args();a['consumer_edges']=[]
    with pytest.raises(ValueError): V.replay(**a)


def test_candidate_not_actual_deadline_and_no_arbitrary_C_selection():
    p=J.candidate()
    assert p['wire_identity_gap']['header_bits']==128
    assert p['wire_identity_gap']['new_command_bits']==237
    assert p['capacity_and_register_gate']['C'] is None
    assert p['accepted_consumer_endpoints']['actual_consumer_deadline'] is None
    assert not p['RTL_GO'] and not p['new_jobs']


def test_actual_gate_has_no_missing_enrollment_fallback():
    with pytest.raises(KeyError): J.actual_deadline({}, Path('/missing'), Path('/missing'))


def test_actual_gate_rejects_historical_geometry_before_any_trace():
    with pytest.raises(ValueError, match='geometry'):
        J.actual_deadline({'parameters': {'ROM_PHW': 6, 'X_ROM': 0}}, Path('/missing'), Path('/missing'))


def test_derived_calendar_preserves_frozen_Nash_source_with_exact_transform():
    base=Path(__file__).resolve().parents[1]
    src=(base/'results/uarch/dsrom_I66_single_joined_candidate_20261002/inputs/Nash_drain_calendar.py.txt').read_text()
    old="                t=edge+Fraction(credit_return_delay);credit_returns.setdefault(t,[]).append(r)\n                if t not in queued:heapq.heappush(heap,t);queued.add(t)\n"
    anchor="                own.mark_visible(r,ctx);journal.append(dict(kind='home_visible',row=r,time=str(edge)))\n"
    expected=src.replace(old,'').replace(anchor,anchor+old)
    expected=expected.replace('PASS_FINITE_SUPPLIED_EDGE_CONTRACT_ONLY','PASS_VISIBILITY_ANCHORED_SUPPLIED_EDGE_CONTRACT_ONLY')
    expected=expected.replace('Consumer edges are *accepted* ready opportunities from the supplied provider,','Credit return is scheduled from actual supplied home visibility, not delivery.\n    Consumer edges are *accepted* ready opportunities from the supplied provider,')
    assert (base/'tools/dsrom_I66_visibility_anchored_calendar.py').read_text()==expected
    assert (base/'tools/dsrom_I66_capture_drain_calendar.py').read_text()==src
