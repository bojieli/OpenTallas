import gzip
import importlib.util
import json
from pathlib import Path
import shutil
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('fastpath',ROOT/'tools/ds_pc01_checkpoint_fastpath_review.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def test_source_replay():
    assert (m.D/'model.json').read_bytes()==m.canonical(m.model())+b'\n'


def test_complete_source_versions_and_shapes():
    a=m.model();g=a['intended_gate']
    assert g['full_native_PCs']==2213 and g['full_homes']==290730
    assert g['capture_boundary']==0 and g['cold_next_PC']==1
    assert [r['publication_records'] for r in a['operator_prices']]==[384,192]
    assert sum(r['sector_requests_upper'] for r in a['operator_prices'])==1608288
    assert a['RAM']['source_PC01_sector_union']==738048
    assert a['RAM']['source_PC01_port_count']==96
    assert a['RAM']['raw_source_state_removed'] is False


def test_lossless_frames_and_index_not_ratio():
    a=m.model();f=a['source_compact_frame_proof']
    assert f['max_frame_bytes']==164 and f['events_per_request']==8
    assert f['sparse_index_charged_every_event'] and f['no_event_drop']
    assert a['disk']['fresh_producer_and_cold_journals']==2388276284
    assert a['disk']['total_fresh_run_bytes']==7836843478


def test_no_constructor_or_launch_admission():
    a=m.model()
    assert not a['implementation_go'] and a['actual_constructor_runs']==a['numeric_runs']==0
    assert a['old_R64_guard_unchanged']
    assert a['RAM']['primary_proposal_retain_reviewed_RAM_bytes']==129877099956
    assert not a['RAM']['prospective_replacement_admitted']
    assert all(not a['prospective_hosts'][h]['resource_admission'] for h in ('PVE1','agidock128'))
    assert not a['physical_parent']['physical_admission']


def test_actual_weights_external_not_checkpoint_or_oracle():
    a=m.model();d=a['disk']
    assert d['selected_PC01_shards_bytes']==8713617304
    assert d['full_released_weights_bytes']==510296708312
    assert d['released_weights_embedded_in_checkpoint_bytes']==0
    assert not d['weights_source_transfer_verified']
    assert not a['intended_gate']['expected_bytes_as_restore_payload']


def test_rename_streaming_does_not_make_second_copy():
    a=m.model();d=a['disk']
    assert d['same_filesystem_atomic_rename_payload_copy_bytes']==0
    assert d['staging_plus_latest_plus_previous_checkpoint_peak']==3*d['new_checkpoint_upper']
    assert d['retained_historical_journals_never_pruned'] and d['failed_staging_not_deleted']


def test_tmpfs_cannot_be_persistent_disk_budget():
    a=m.model()['prospective_hosts']['agidock128']
    assert a['tmp']['type']=='tmpfs' and a['disk_path']=='/home/ubuntu'
    assert a['tmp']['total_bytes']==67487199232


def test_KSM_PSS_is_not_full_COW():
    a=m.model()['physical_parent']
    assert a['full_known_shared_COW_plus_unbacked_delta_bytes']==71281614848
    assert a['current_known_no_credit_COW_deficit_bytes']==14134427648
    assert a['PSS_difference_not_full_COW_cost'] and a['guest_plus_host_not_summed']
    assert a['host_reclaim_credit_bytes']==0


def test_retired_candidate_not_synthetic_release():
    a=m.model()['physical_parent']
    assert a['W6_cache_candidate_resident_bytes']==16674668544
    assert not a['cache_cleanliness_verified']
    assert a['owner_confirmed_retired_clean_files']==0
    assert not a['observed_guest_cache_eviction_alone_is_host_credit']
    assert not a['physical_reporting_or_discard_mechanism_verified']
    assert a['cache_NFS_TCP2049']=='unreachable'


@pytest.mark.parametrize('B,U,S,expected',[(130,1,70,71),(40,1,70,40),(130,2,0,2),(0,2,70,0)])
def test_physical_private_reuse_bound(B,U,S,expected):
    assert m.host_delta(allocation=B,unbacked=U,shared_resident=S)==expected


def test_negative_physical_cost_refused():
    with pytest.raises(ValueError,match='nonnegative'):m.host_delta(allocation=-1,unbacked=0,shared_resident=1)


@pytest.fixture
def inputs(tmp_path):
    p=tmp_path/'inputs';shutil.copytree(m.D/'inputs',p);return p


@pytest.mark.parametrize('rel',['sources/tools/ds_producer_checkpoint_resume_v3.py',
    'sources/tools/h3_complete_native_calendar_successor_r1.py','PC01_metadata_slice.json.gz',
    'physical_capacity_cc4d.json','cache_inventory_de930.json'])
def test_changed_identity_refused(inputs,rel):
    p=inputs/rel;p.write_bytes(p.read_bytes()+b'x')
    with pytest.raises(ValueError,match='input changed'):m.model(inputs)


def test_partial_RF_shape_is_not_capacity_credit(inputs):
    p=inputs/'PC01_metadata_slice.json.gz';data=m.load(p)
    key=next(iter(data['homes']));data['homes'][key]['word_count']+=1
    frame=m.compact_primitives(inputs)
    with pytest.raises(ValueError,match='source F32 output/home extent'):
        m.operator_prices(data,frame)


def test_64_bit_scalar_frame_is_priced(inputs):
    f=m.compact_primitives(inputs)
    a=f(dict(event='x',identity={'tag':(1<<64)-1},allocation_identity={'rank':95},payload_sha256='f'*64))
    assert a['integer_fields']==1 and a['frame_bytes_upper']>=62
    assert a['metadata']=={'rank':95}


def test_no_rank_narrowing(inputs):
    p=inputs/'PC01_metadata_slice.json.gz';a=m.load(p);a['instructions'][0]['rank_bindings'].pop()
    with pytest.raises(ValueError,match='full96 rank coverage'):m.operator_prices(a,m.compact_primitives(inputs))


def test_legacy_actual_peak_does_not_qualify_cold_restore():
    a=m.model()['RAM']
    assert a['measured_R58_one_producer_PC0_9_peak_bytes']==12994072*1024
    assert a['measured_RSS_not_used_as_launch_upper_bound']
    assert not a['measured_R58_dual_constructor_capture_restore']
