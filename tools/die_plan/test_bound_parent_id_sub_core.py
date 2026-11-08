"""DIE-HBM-90-TSTRAP 11-07: a sub-core's declared parent ID strap is checked on the as-built leaf that holds it.

The bind (Binder.__init__, exact asbuilt.sub_core_leaf table) promotes plan hard core u_sfucore_Q_lane14__fr
(physical_inst u_sfucore_Q_lane14.u_fcore.u_core.u_fr) as strap_u_sfucore_Q_lane14_map_lane_j on leaf
u_sfucore_Q_lane14.  gen_phys must resolve the plan declaration with the same table (from the producer manifest
the kit records), else 8 HBM types stop on 'bound parent ID ... disagrees with plan or kit ports'.
"""
import json
from copy import deepcopy
import pytest
from tools.die_plan.gen_phys import bound_parent_id_plan, logical_strap_names

NAME = 'strap_u_sfucore_Q_lane14_map_lane_j'


def vehicle(tmp_path, table=None, desc_extra=None, row_leaf='u_sfucore_Q_lane14', record_manifest=True):
    desc = dict(inst='u_sfucore_Q_lane14__fr', module='ot_hgi_sfu_split3_lane_core_fr',
                physical_inst='u_sfucore_Q_lane14.u_fcore.u_core.u_fr',
                parent_id_straps={'map_lane_j': {'width': 4, 'value': 14}}, **(desc_extra or {}))
    raw = dict(partition_types=dict(t=dict(hard_cores=[desc])))
    (tmp_path / 'bind_parent_id_straps.json').write_text(json.dumps(
        dict(types=dict(t={NAME: dict(leaf=row_leaf, port='map_lane_j', width=4)}))))
    ab = tmp_path / 'asbuilt.json'
    ab.write_text(json.dumps({} if table is None else dict(sub_core_leaf=table)))
    meta = dict(bind_out=str(tmp_path), bound_type='t', bound_only_pins=[dict(port=NAME, dir='input', width=4)])
    if record_manifest:
        meta['asbuilt_manifest'] = str(ab)
    (tmp_path / 'kit_rtl.json').write_text(json.dumps(meta))
    return raw, {'t': tmp_path / 'kit_rtl.f'}


def test_sub_core_id_resolves_on_bound_leaf(tmp_path):
    raw, files = vehicle(tmp_path, table={'u_sfucore_Q_lane14': 'u_sfucore_Q_lane14'})
    before = deepcopy(raw)
    got = bound_parent_id_plan(raw, files)
    assert raw == before
    assert logical_strap_names(got['partition_types']['t']) == [NAME]
    assert got['partition_types']['t']['id_straps'] == [dict(name=NAME, width=4)]


def test_sub_core_parent_path_resolves(tmp_path):
    raw, files = vehicle(tmp_path, table={'u_par': 'u_sfucore_Q_lane14'},
                         desc_extra=dict(sub_core_parent='u_par'))
    raw['partition_types']['t']['hard_cores'][0]['physical_inst'] = 'u_par.u_x.u_fr'
    got = bound_parent_id_plan(raw, files)
    assert logical_strap_names(got['partition_types']['t']) == [NAME]


@pytest.mark.parametrize('case', ['no_table', 'no_manifest', 'other_leaf', 'row_unrelated', 'explicit_wins'])
def test_no_guessing(tmp_path, case):
    kw = dict(table={'u_sfucore_Q_lane14': 'u_sfucore_Q_lane14'})
    if case == 'no_table':
        kw = dict(table=None)
    if case == 'no_manifest':
        kw['record_manifest'] = False
    if case == 'other_leaf':
        kw = dict(table={'u_sfucore_Q_lane14': 'u_sfucore_Q_lane15'})
    if case == 'row_unrelated':
        kw['row_leaf'] = 'u_sfucore_Q_lane15'
    if case == 'explicit_wins':
        kw['desc_extra'] = dict(parent_id_leaf='u_elsewhere')
    raw, files = vehicle(tmp_path, **kw)
    with pytest.raises(ValueError, match='disagrees with plan or kit ports'):
        bound_parent_id_plan(raw, files)


def test_shared_rule_matches_binder():
    from tools.die_plan.parent_id_straps import sub_core_bound_leaf, with_sub_core_id_leaves
    table = {'u_a': 'u_a', 'u_p': 'u_b'}
    assert sub_core_bound_leaf(dict(physical_inst='u_a.u_fcore.u_core.u_fr'), table) == 'u_a'
    assert sub_core_bound_leaf(dict(physical_inst='u_a.u_core.u_fr'), table) is None
    assert sub_core_bound_leaf(dict(sub_core_parent='u_p', physical_inst='u_a.u_fcore.x'), table) == 'u_b'
    assert sub_core_bound_leaf(dict(physical_inst='u_z.u_fcore.u_core.u_fr'), table) is None
    t = dict(hard_cores=[dict(inst='u_a__fr', physical_inst='u_a.u_fcore.u_core.u_fr', parent_id_straps={'x': 1}),
                         dict(inst='u_a__bk', physical_inst='u_a.u_fcore.u_core.u_bk')])
    got = with_sub_core_id_leaves(t, table)
    assert got['hard_cores'][0]['parent_id_leaf'] == 'u_a' and 'parent_id_leaf' not in got['hard_cores'][1]
    assert 'parent_id_leaf' not in t['hard_cores'][0]
    assert with_sub_core_id_leaves(t, {}) is t
