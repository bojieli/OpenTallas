import ast
import importlib.util
import json
import shutil
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('r64audit',ROOT/'tools/ds_hbm_r64_scope_audit.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def test_archived_whole_audit():
    a=m.audit()
    assert a['phases'][0]['required_RAM_bytes']==129877099956
    assert a['phases'][0]['required_disk_bytes']==528693705466
    assert a['source_snapshots']==52 and a['original_artifacts']==8
    assert a['prospective_PVE1']['placement_admitted'] is False
    assert a['complete_continuation_scopes']==43
    assert a['resource_admission'] is False


def test_model_byte_replay():
    assert (ROOT/'results/uarch/ds_hbm_r64_independent_scope_audit_20261003/model.json').read_bytes()==m.canonical(m.audit())+b'\n'


@pytest.fixture
def archived(tmp_path):
    d=tmp_path/'inputs';shutil.copytree(m.DEFAULT,d);return d


@pytest.mark.parametrize('name',[
    'sources/tools/ds_hbm_checkpointed_prefix_r63.py',
    'sources/tools/ds_hbm_dual_constructor_r64.py',
    'preflight_plan.json','preflight_model.json','phase_component_evidence/continuation_model.json'])
def test_source_or_record_tamper_refused(archived,name):
    p=archived/name;p.write_bytes(p.read_bytes()+b' ')
    with pytest.raises(ValueError,match='archived input changed'):m.audit(archived)


def test_partial_inventory_refused(archived):
    (archived/'sources/tools/ds_hbm_checkpointed_prefix_r63.py').unlink()
    with pytest.raises(ValueError,match='complete archived input inventory'):m.audit(archived)


def test_guard_removed_source_predicate(archived):
    p=archived/'sources/tools/ds_hbm_checkpointed_prefix_r63.py'
    raw=p.read_text().replace('admitted=source_gate(plan,available_bytes=stat.f_bavail*stat.f_frsize)',
                             'admitted=skip_gate(plan)')
    p.write_text(raw)
    with pytest.raises(StopIteration):m.source_scope(archived)


def test_preflight_operation_is_rejected(archived):
    p=archived/'sources/tools/ds_hbm_checkpointed_prefix_r63.py'
    p.write_text(p.read_text().replace('if args.preflight_only:\n',
            'if args.preflight_only:\n            engine.execute_operation(native["instructions"][0])\n'))
    with pytest.raises(ValueError,match='numerical/capture/restore'):m.source_scope(archived)


def test_shared_eager_allocation_refused(archived):
    p=archived/'sources/tools/h4_hbm_w19_pc10_endpoints.py'
    p.write_text(p.read_text().replace('self.budget=budget;self.memories={};self.sources=inputs()',
                                     'self.budget=budget;self.memories={};self.sources=BoundSectorProvider()'))
    with pytest.raises(ValueError,match='raw ports must be lazy'):m.source_scope(archived)


def test_registered_loader_after_constructor_rejected(archived):
    p=archived/'sources/tools/ds_hbm_dual_constructor_r64.py'
    p.write_text(p.read_text().replace('enrollment.install()\n    original.main()',
                                     'original.main()\n    enrollment.install()'))
    with pytest.raises(ValueError,match='registered loader order'):m.source_scope(archived)


def test_diagnostic_undercharge_refused(archived):
    p=archived/'preflight_model.json';a=json.loads(p.read_bytes())
    a['R64_additive_costs']['RAM_extra_bytes']-=1;p.write_bytes(m.canonical(a))
    # Bypass outer hashes only to exercise independent arithmetic rejection.
    q=archived/'preflight_plan.json';b=json.loads(q.read_bytes());b['storage_proof']['sha256']=m.sha(p);q.write_bytes(m.canonical(b))
    with pytest.raises(ValueError,match='diagnostic RAM charge'):
        m.model_totals(archived,'preflight',True,m.read(archived,'source_snapshot_sha256.json'))


def test_journal_not_ram_and_actual_unknown():
    a=m.audit();n=a['PC11_19']
    assert n['journal_is_disk_not_RAM'] and n['actual_numeric_PASS'] is None
    assert n['CPU_native_live_and_transient_bytes']==14333360
    assert n['compact_journal_component_bytes']==3132192*45056
    assert all(p['whole_runtime_projection_complete'] is False for p in n['per_PC_components'])


def test_PC19_I64_pair_of_words():
    a=m.audit();rows=a['typed_output_home_checks']['rows']
    r=next(r for r in rows if r['PC']==19 and r['result']=='route_ids')
    assert r['dtype']=='I64' and r['elements']==6 and r['bytes_per_rank']==48
    assert r['ranks_checked']==96
    assert {r['PC'] for r in rows}==set(range(11,20))


def test_I64_home_truncation_rejected(archived):
    import gzip
    p=archived/'PC11_19_native_home_slice.json.gz';a=json.loads(gzip.decompress(p.read_bytes()))
    for h in a['homes']:
        if h['name']=='route_ids':h['word_count']=6
    p.write_bytes(gzip.compress(m.canonical(a),mtime=0))
    with pytest.raises(ValueError,match='typed writer/home byte extent'):m.typed_home_audit(archived)


def test_noalias_source_path_identity_rejected(archived):
    import gzip
    p=archived/'actual_manifest.json.gz';a=json.loads(gzip.decompress(p.read_bytes()))
    a['initial_versions'][1]['path']=a['initial_versions'][0]['path']
    a['initial_versions'][1]['sha256']='0'*64
    p.write_bytes(gzip.compress(m.canonical(a),mtime=0))
    with pytest.raises(ValueError,match='conflicting payload identity'):m.initial_aliases(archived)


def test_constructor_source_aliases_not_zero_charge():
    a=m.audit()['initial_source_aliases']
    assert a['initial_version_records']==3840 and a['unique_readonly_paths']==40
    assert a['embedding_F32_repeat_bytes_per_constructor']==81920
    assert a['no_mapping_RAM_discount_applied']
