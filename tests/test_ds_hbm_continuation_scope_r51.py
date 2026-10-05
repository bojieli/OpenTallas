import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import ds_hbm_continuation_scope_r51 as c


def inputs():
    old = dict(prefix_stop=9, journal_root='/old', journal_capacity_bytes=100,
               native='exact', homes='exact', tags=1, backing_bytes=33554432,
               generation=1, initial_versions=[dict(sha256='payload')])
    new = dict(old, prefix_stop=10, journal_root='/new', journal_capacity_bytes=200)
    def identity(m):
        x=dict(m); x.pop('journal_root')
        return dict(manifest_sha256=c.digest(x), native_sha256='n', homes_sha256='h',
                    source_sha256={'helper':'s'}, retention_policy_sha256='r', generation=1)
    return [old, new, identity(old), identity(new)]


def run(args, **kw):
    return c.transition(*args, boundary_pc=9,
        storage_projection=kw.get('storage', dict(required_new_bytes=300, available_bytes=400,
                                                  continuation_new_bytes=200)),
        source_review={'source_sha256':'source', 'review_record_sha256':'review'})


def test_explicit_scope_extension_does_not_mutate_or_grant():
    args=inputs(); before=copy.deepcopy(args); record=run(args)
    assert args==before and record['old_policy']['prefix_stop']==9
    assert record['new_policy']['prefix_stop']==10
    assert not record['numerical_GO'] and not record['actual_state_restored']
    assert not record['constructor_admitted']
    digest=record.pop('transition_sha256'); assert digest==c.digest(record)


@pytest.mark.parametrize('field,value', [('tags',2),('backing_bytes',67108864),
 ('native','mutant'),('homes','mutant'),('generation',2),('initial_versions',[])])
def test_data_or_physical_change_refuses_before_side_effect(field,value):
    args=inputs(); args[1][field]=value; before=copy.deepcopy(args)
    with pytest.raises(ValueError, match='data/backing'):run(args)
    assert args==before


@pytest.mark.parametrize('field', ['native_sha256','homes_sha256','source_sha256','retention_policy_sha256'])
def test_other_identity_not_relaxed(field):
    args=inputs();args[3][field]='changed'
    with pytest.raises(ValueError,match='program/homes'):run(args)


def test_manifest_hash_is_not_waived():
    args=inputs();args[3]['manifest_sha256']='wrong'
    with pytest.raises(ValueError,match='actual declared'):run(args)


@pytest.mark.parametrize('storage', [dict(required_new_bytes=401,available_bytes=400,continuation_new_bytes=200),
 dict(required_new_bytes=300,available_bytes=400,continuation_new_bytes=199)])
def test_incomplete_disk_projection_refuses(storage):
    with pytest.raises(ValueError):run(inputs(),storage=storage)
