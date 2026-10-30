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
