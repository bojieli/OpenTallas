import importlib.util
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('plan',Path(__file__).parents[1]/'tools/w17_window_recovery_candidate_plan.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def test_bounded_uarch_ledger():
    p=m.build_plan();e=p['element']
    assert e['storage_bits']==sum(e['storage_bits_by_resource'].values())==276
    assert e['area_est_um2']==pytest.approx(276*.2916+256*.2+512)
    assert e['replicas_fixed']==1 and e['macs_per_element']==0
    assert e['entries']['read_owned_max']==8
    assert e['entries']['write_unissued_total_max']==1
    assert p['routing']['total_point_to_point_conductor_segments']==24
    assert e['ports_per_element']['request_bits']==1+30+4+17+1+256+32+1
    assert e['ports_per_element']['response_bits']==1+17+4+256+1


def test_plan_only_and_source_pinned():
    p=m.build_plan()
    assert p['budget']['compile_GO'] is False
    assert p['source_commit']=='4e38326d6f361bc85e660f48c59c355e2bb95274'
    assert p['manifest']['sources']==145
    assert p['element']['parameters']['OPT_RECOVERY']==0
    copies=p['planned_added_paths']['copies']
    assert len(copies)==5
    for v in copies.values(): assert len(v['from']['sha256'])==64
    assert copies['window_prefetch_recovery.sv']['from']['commit'].startswith('c09f3fe15')
    assert 'not physical' in p['budget']['remaining_physical_gate']
    assert p['latency']['healthy_added_pipeline_cycles']==0
    assert p['budget']['cpus_max']==2 and p['budget']['memory_GiB_max']==4
    assert p['budget']['whole_field_die_builds']==0
