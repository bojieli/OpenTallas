"""A cached placement must not survive a changed physical interface."""
import copy
import json
from pathlib import Path

import b2o


def seed_fixture(tmp_path):
    (tmp_path / 'pins.json').write_text('[{"name":"clk","x":0,"y":1,"layer":"M4"}]')
    raw = dict(partition_types={'t': dict(module='t', outline_um=[100, 80],
                   hard_cores=[dict(inst='c', module='c', outline_um=[20, 20],
                                    origin_um=[10, 10], pins_file='pins.json')],
                   contents=[dict(inst='c', module='c', outline_um=[20, 20], origin_um=[10, 10])])},
               partitions=[dict(name='p', type='t')],
               ports=[dict(id='a', src=dict(part='p', bus='data'), dst=dict(part='@die', bus='out'),
                           width=4, kind='data', face='S', window_um=[1, 5], layers=['M5'])])
    path = tmp_path / 'plan.json'
    path.write_text(json.dumps(raw))
    seed = b2o.placement_seed(path)
    raw = copy.deepcopy(raw)
    raw['partition_types']['t']['hard_cores'][0]['origin_um'] = [60, 50]
    seed['current_ports'] = seed['port_fingerprint'](raw)
    return raw, seed


def test_exact_interface_reuses_geometry(tmp_path):
    raw, seed = seed_fixture(tmp_path)
    assert b2o.reuse_placement('t', raw, tmp_path, seed)
    assert raw['partition_types']['t']['hard_cores'][0]['origin_um'] == [10, 10]


def test_changed_pin_view_blocks_reuse(tmp_path):
    raw, seed = seed_fixture(tmp_path)
    (tmp_path / 'pins.json').write_text('[{"name":"clk","x":2,"y":1,"layer":"M4"}]')
    assert not b2o.reuse_placement('t', raw, tmp_path, seed)


def test_changed_bus_window_blocks_reuse(tmp_path):
    raw, seed = seed_fixture(tmp_path)
    raw['ports'][0]['window_um'] = [8, 12]
    seed['current_ports'] = seed['port_fingerprint'](raw)
    assert not b2o.reuse_placement('t', raw, tmp_path, seed)
