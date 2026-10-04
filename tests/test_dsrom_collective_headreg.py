import hashlib
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import dsrom_collective_headreg as H


def test_actual_c8_source_join(tmp_path):
    # Exact declared C8 parent instance/parameter interfaces; no fake ports.
    die = tmp_path / 'inputs' / 'ot_chip_v41x_die_owner_safe_c8.sv'
    die.parent.mkdir()
    die.write_text('module ot_chip_v41x_die_owner_safe_c8 #(\n    parameter integer C8_PUBLICATION=0,\nparameter integer X=0)();\not_w15_rom_oneshot_die_px #(.N(4)) u_coll();\nendmodule\n')
    top = die.with_name('ot_v41_rt_die_l20_c8.sv')
    top.write_text('module ot_v41_rt_die_l20_c8 #(\n    parameter integer C8_PUBLICATION=0,\nparameter integer X=0)();\not_chip_v41x_die_owner_safe_c8 #(.X(X)) dut();\nendmodule\n')
    before = [p.read_bytes() for p in (die, top)]
    r = H.install([die, top], tmp_path/'selected')
    assert r['parameters'] == {'COLL_HEADREG': 0}
    assert [p.read_bytes() for p in (die, top)] == before
    assert '.REGISTER_HEAD(COLL_HEADREG)' in r['sources'][0].read_text()
    assert '.COLL_HEADREG(COLL_HEADREG)' in r['sources'][1].read_text()
    assert r['sources'][-1] == ROOT/H.ENGINE
    assert H.install([die,top], tmp_path/'selected',enable=True)['parameters']['COLL_HEADREG']==1
    for p in r['sources']:
        assert hashlib.sha256(p.read_bytes()).hexdigest()==r['source_sha256'][str(p)]
    with pytest.raises(ValueError): H.install([die,die,top],tmp_path/'other')
    with pytest.raises(ValueError): H.install([die],tmp_path/'other')
    with pytest.raises(ValueError): H.install([die,top],die.parent)


def test_per_actual_collective_price():
    r=H.price_collectives(['token100:coll0','token100:coll1','token101:coll0'],clock_hz=.9e9)
    assert r['added_cycles']==3
    assert r['added_seconds']==3/.9e9
    assert r['extra_state_bits_per_die']==4384
    assert r['external_boundary_added_bits']==r['fifo_capacity_change']==r['II_change']==0
    assert not r['adopted'] and not r['clock_fit']
    with pytest.raises(ValueError): H.price_collectives(['same','same'])
