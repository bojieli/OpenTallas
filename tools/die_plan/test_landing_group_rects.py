import subprocess
from copy import deepcopy
import pytest
from tools.die_plan.landing_place import _group_rect_overrides

TYPE = {'outline_um': [100, 100], 'clock': {'landing_contract': {}}}
GROUPS = [('u_cland_collect_rst_n_t2', [8, 8, 12, 12], 'collector:rst_n_t2'),
          ('u_cland_rst_bus', [8, 8, 12, 12], 'raw-copy-optional'),
          ('u_cland_bus', [20, 20, 40, 40], 'ring:bus')]
PREFIX = 'u_cland_collect_rst_n_t2'


def configured(value):
    t = deepcopy(TYPE)
    t['clock']['landing_contract']['group_rects_um'] = value
    return t


def test_absent_and_empty_leave_output_unchanged():
    assert _group_rect_overrides(TYPE, GROUPS) == (GROUPS, '')
    assert _group_rect_overrides(configured({}), GROUPS) == (GROUPS, '')


def test_changes_only_exact_supported_group():
    out, check = _group_rect_overrides(configured({PREFIX: [15, 16, 25, 26]}), GROUPS)
    assert out[0] == (PREFIX, [15, 16, 25, 26], 'collector:rst_n_t2')
    assert out[1:] == GROUPS[1:]
    assert 'unused group rectangle override' in check


@pytest.mark.parametrize('bad', [None, [], 0, {'u_cland_missing': [1, 1, 2, 2]},
    {'u_cland_bus': [1, 1, 2, 2]}, {PREFIX: [1, 1, 1, 2]},
    {PREFIX: [-1, 1, 2, 2]}, {PREFIX: [1, 1, 101, 2]},
    {PREFIX: [True, 1, 2, 2]}, {PREFIX: [1, 1, float('nan'), 2]},
    {PREFIX: [1, 1, float('inf'), 2]}])
def test_bad_or_unsupported_override_rejected(bad):
    with pytest.raises(ValueError):
        _group_rect_overrides(configured(bad), GROUPS)


@pytest.mark.parametrize('actual,accepted', [(PREFIX, True),
    ('u_cland_collect_rst_n_t20', False), ('u_cland_other', False)])
def test_mapped_inventory_required(tmp_path, actual, accepted):
    _, check = _group_rect_overrides(configured({PREFIX: [15, 16, 25, 26]}), GROUPS)
    script = ('proc block {cmd} {return {cell}}\n'
              f'proc cell {{cmd}} {{return {{u_bound.{actual}/q}}}}\n'
              'set ff_blk block\n' + check)
    p = tmp_path / 'inventory.tcl'
    p.write_text(script)
    r = subprocess.run(['tclsh', str(p)], text=True, capture_output=True)
    assert (r.returncode == 0) == accepted
    if not accepted:
        assert 'unused group rectangle override' in r.stderr


@pytest.mark.parametrize('present', [True, False])
def test_optional_copy_absent_only_logs(tmp_path, present):
    name = 'u_cland_rst_bus' if present else 'u_cland_other'
    _, check = _group_rect_overrides(configured({'u_cland_rst_bus': [15, 16, 25, 26]}), GROUPS)
    script = ('proc block {cmd} {return {cell}}\n'
              f'proc cell {{cmd}} {{return {{u_bound.{name}/q}}}}\n'
              'set ff_blk block\n' + check)
    p = tmp_path / 'inventory.tcl'
    p.write_text(script)
    r = subprocess.run(['tclsh', str(p)], text=True, capture_output=True)
    assert r.returncode == 0
    assert ('no mapped instance, skipped' in r.stdout) == (not present)


# GEN-CLASS-1 11-12: QC sle_ctl__cl372cea1c gen 'unknown ... landing group override u_cland_collect_rst_n_t19'.
STALE = {'u_cland_collect_rst_n_t19': 'collector node rst_n_t19 is in the tree but on no active path (tree re-solved)',
         'u_cland_reset_rst_n_t19': 'collector node rst_n_t19 is in the tree but on no active path (tree re-solved)'}


def test_stale_inactive_collector_override_dropped_and_logged():
    out, check = _group_rect_overrides(configured({'u_cland_collect_rst_n_t19': [15, 16, 25, 26]}), GROUPS, STALE)
    assert out == GROUPS
    assert 'stale group rectangle override u_cland_collect_rst_n_t19' in check
    assert 'unused group rectangle override' not in check


def test_stale_mixed_with_live_override_keeps_live_one():
    out, check = _group_rect_overrides(configured({'u_cland_collect_rst_n_t19': [1, 1, 2, 2],
                                                   PREFIX: [15, 16, 25, 26]}), GROUPS, STALE)
    assert out[0] == (PREFIX, [15, 16, 25, 26], 'collector:rst_n_t2')
    assert 'stale group rectangle override u_cland_collect_rst_n_t19' in check
    assert 'unused group rectangle override' in check


def test_non_tree_prefix_still_fails_closed():
    with pytest.raises(ValueError, match='unknown, ambiguous or unsupported'):
        _group_rect_overrides(configured({'u_cland_collect_rst_n_t99': [1, 1, 2, 2]}), GROUPS, STALE)


def test_tcl_drops_override_on_inactive_tree_node():
    """tcl(): rst_n_t19 hangs off the root but no source path uses it -> its override is a logged no-op."""
    from types import SimpleNamespace
    from tools.die_plan import landing_place as LP
    tree = dict(root=[50, 2], relays=[
        dict(name='u_rrl_0', xy=[50, 10], d='rst_root_n', q='rst_rl_0', depth=1, tap=2, kind='pad'),
        dict(name='u_rrl_1', xy=[20, 20], d='rst_rl_0', q='rst_n_t2', depth=2, tap=2, kind='tap'),
        dict(name='u_rrl_2', xy=[80, 20], d='rst_rl_0', q='rst_n_t19', depth=2, tap=19, kind='tap')])
    lc = dict(collector_tree=tree, collector_root_node='rst_root_n',
              collector_local_sources=[dict(name='bus', tap=2, xy_um=[0, 20])], collector_children=[],
              group_rects_um={'u_cland_collect_rst_n_t19': [70, 70, 74, 74]})
    t = dict(outline_um=[100, 100], clock=dict(landing_contract=lc))
    P = SimpleNamespace(types={'ty': t}, clock={})
    out = LP.tcl(P, 'ty')
    assert 'OT_CLAND stale group rectangle override u_cland_collect_rst_n_t19' in out
    assert 'u_cland_collect_rst_n_t2 ' in out and '{u_cland_collect_rst_n_t19 ' not in out
    lc['group_rects_um'] = {'u_cland_collect_rst_n_t7': [70, 70, 74, 74]}
    with pytest.raises(ValueError, match='unknown, ambiguous or unsupported'):
        LP.tcl(P, 'ty')
