"""No-local-SU source specialization rejects an executable calendar grant."""
import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('vm_calendar', Path(__file__).resolve().parents[1] / 'hbm_vm_static_calendar.py')
VM = importlib.util.module_from_spec(spec); spec.loader.exec_module(VM)


def layout(role='SW'):
    widths = dict(client_seq=10, response_enable=5, response_seq=10, bank_enable=8, bank_client=24,
                  hub_ring_enable=2, hub_ring_client=6, rslot_v=8, wslot_v=8, rslot=24, wslot=24,
                  ring_tx_enable=2, ring_tx_source=6, replay_enable=1, replay_source=1,
                  lg_local_read=24, lg_local_write=24)
    fields=[]; lo=0
    for name in VM.FIELDS:
        fields.append(dict(name=name, lo=lo, bits=widths[name])); lo += widths[name]
    return dict(quadrant=role, params=dict(RG=5,WG=2,NC=2,RB=3,WB=3,CW=3),fields=fields)


@pytest.mark.parametrize('mode', ['SU','MTP','MU'])
def test_other_clients_unchanged(mode):
    # Banks grant SM write group1 and DMA group2; reads group1..5 (5 is ring).
    cycles=[dict(rslot_v=255, rslot=sum(owner << (3*b) for b in range(8)),
                 wslot_v=255, wslot=sum((1+(owner%2)) << (3*b) for b in range(8))) for owner in range(1,6)]
    s=dict(cycles=cycles,loops=2)
    base=VM.compile_schedule(layout(),s)
    restricted=VM.compile_schedule(layout(),dict(s,local_su_present=False,build_mode=mode))
    assert restricted['configuration_writes']==base['configuration_writes']
    assert restricted['local_su_absence']['checked_build_mode']==mode
    assert restricted['output_edges']==10


@pytest.mark.parametrize('mode', ['SU','MTP','MU'])
@pytest.mark.parametrize('field', ['rslot_v','wslot_v','lg_local_read','lg_local_write'])
def test_missing_source_schedule_refused(mode,field):
    s=dict(local_su_present=False,build_mode=mode,cycles=[{}, {field:1}])
    with pytest.raises(ValueError,match='absent local SU'):
        VM.compile_schedule(layout(),s)


def test_no_implicit_mode_or_north_absence():
    with pytest.raises(ValueError,match='build_mode'):
        VM.compile_schedule(layout(),dict(local_su_present=False,cycles=[{}]))
    with pytest.raises(ValueError,match='SW/SE'):
        VM.compile_schedule(layout('NW'),dict(local_su_present=False,build_mode='SU',cycles=[{}]))


@pytest.mark.parametrize('mode', ['SU','MTP','MU'])
def test_backing_memory_retains_real_idx_and_ring_words(mode):
    cycles=[dict(rslot_v=255,rslot=sum(r << (3*b) for b in range(8)),
                 wslot_v=255,wslot=sum(w << (3*b) for b in range(8))) for r in (4,5) for w in (3,4,5)]
    base=VM.compile_schedule(layout(),dict(cycles=cycles))
    result=VM.compile_schedule(layout(),dict(cycles=cycles,local_su_present=False,build_mode=mode,s_role_backing_only=True))
    assert result['configuration_writes']==base['configuration_writes']
    assert result['s_role_backing_only']['allowed_read_groups']==[4,5]


@pytest.mark.parametrize('kind,owner', [('r',1),('r',2),('r',3),('w',1),('w',2),('w',6)])
def test_absent_s_role_service_grant_refused(kind,owner):
    schedule=dict(local_su_present=False,build_mode='MTP',s_role_backing_only=True,
                  cycles=[{kind+'slot_v':1,kind+'slot':owner}])
    with pytest.raises(ValueError,match='absent S-role service'):
        VM.compile_schedule(layout(),schedule)
