import json
from copy import deepcopy
from pathlib import Path
import pytest
from tools.die_plan.gen_phys import bound_parent_id_plan, logical_strap_pin_records, logical_strap_names


def vehicle(tmp_path):
    desc = dict(inst='head2_e0', module='kv3_head_eighth_e0',
                straps=[dict(port='strap_hid', width=2, value="2'b10")])
    raw = dict(partition_types=dict(t=dict(hard_cores=[desc])))
    name = 'strap_head2_e0_strap_hid'
    manifest = dict(types=dict(t={name:dict(leaf='head2_e0', port='strap_hid', width=2)}))
    (tmp_path/'bind_parent_id_straps.json').write_text(json.dumps(manifest))
    meta = dict(bind_out=str(tmp_path), bound_type='t', bound_only_pins=[dict(port=name,dir='input',width=2)])
    (tmp_path/'kit_rtl.json').write_text(json.dumps(meta))
    return raw, {'t':tmp_path/'kit_rtl.f'}, manifest, meta, name


def test_declared_child_id_is_projected_without_plan_mutation(tmp_path):
    raw, files, _, _, name = vehicle(tmp_path)
    before = deepcopy(raw)
    got = bound_parent_id_plan(raw,files)
    assert raw == before
    assert logical_strap_names(got['partition_types']['t']) == [name]
    assert logical_strap_pin_records(got['partition_types']['t']) == [dict(bus=name,bit=0),dict(bus=name,bit=1)]


@pytest.mark.parametrize('bad', ['leaf','width','output','name'])
def test_manifest_cannot_authorize_other_ports(tmp_path,bad):
    raw, files, manifest, meta, name = vehicle(tmp_path)
    if bad == 'leaf': manifest['types']['t'][name]['leaf']='unrelated'
    if bad == 'width': manifest['types']['t'][name]['width']=3
    if bad == 'output': meta['bound_only_pins'][0]['dir']='output'
    if bad == 'name': manifest['types']['t']['strap_invented']=manifest['types']['t'].pop(name)
    (tmp_path/'bind_parent_id_straps.json').write_text(json.dumps(manifest))
    (tmp_path/'kit_rtl.json').write_text(json.dumps(meta))
    with pytest.raises(ValueError): bound_parent_id_plan(raw,files)


def test_plain_kits_are_byte_unchanged():
    raw = dict(partition_types=dict(t={}))
    assert bound_parent_id_plan(raw,None) is raw


def test_existing_count_rows_are_not_child_ids(tmp_path):
    raw, files, manifest, _, _ = vehicle(tmp_path)
    raw['partition_types']['t']['count_straps']=[dict(name='strap_ca_K',width=6)]
    manifest['types']['t']['strap_ca_K']=dict(width=6,kind='count_strap')
    (tmp_path/'bind_parent_id_straps.json').write_text(json.dumps(manifest))
    got=bound_parent_id_plan(raw,files)
    assert len(logical_strap_pin_records(got['partition_types']['t']))==8


def test_child_id_already_declared_top_level_is_not_duplicated(tmp_path):
    # DIE-QC-61 11-01: QC CB types declare child tile_id straps under count_straps; the bind manifest also lists them
    # with their leaf, so promotion must not append a second id_straps row (sdc_lint straps: duplicate names).
    raw, files, _, _, name = vehicle(tmp_path)
    raw['partition_types']['t']['count_straps'] = [dict(name=name, width=2)]
    got = bound_parent_id_plan(raw, files)
    t = got['partition_types']['t']
    assert logical_strap_names(t) == [name]
    assert not t.get('id_straps')


def test_child_id_declared_top_level_with_other_width_fails(tmp_path):
    raw, files, _, _, name = vehicle(tmp_path)
    raw['partition_types']['t']['count_straps'] = [dict(name=name, width=3)]
    with pytest.raises(ValueError):
        bound_parent_id_plan(raw, files)
