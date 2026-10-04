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


def test_selected_s81_reuses_owner_source_factory(tmp_path,monkeypatch):
    from types import SimpleNamespace
    actual_sources=[Path('/owner/actual-native.sv')]
    binding=SimpleNamespace(stages=81,inventory={'TP':4},pairs=2417,
                            contract={'return_contract':{'RD':64}},
                            native_sources=lambda export: actual_sources)
    calls=[]
    def installer(sources,output,*,enable):
        calls.append((sources,output,enable))
        return {'parameters':{'COLL_HEADREG':int(enable)}}
    monkeypatch.setattr(H,'install',installer)
    r=H.install_s81_parent(binding,'original-export',tmp_path,enable=True,
                          actual_collectives=['pos100:coll0','pos101:coll0'])
    assert calls==[(actual_sources,tmp_path,True)]
    assert r['pairs_per_rank_die']==2417 and r['return_depth']==64
    assert r['added_cycles']==2
    assert H.install_s81_parent(binding,'original-export',tmp_path)['added_cycles']==0
    binding.stages=82
    with pytest.raises(ValueError):H.install_s81_parent(binding,'original-export',tmp_path)
    binding.stages=81;binding.contract['return_contract']['RD']=16
    with pytest.raises(ValueError):H.install_s81_parent(binding,'original-export',tmp_path)


def _parent_fixture(tmp_path):
    parent=tmp_path/'inputs';parent.mkdir()
    die=parent/'ot_chip_v41x_die_owner_safe_c8.sv'
    top=parent/'ot_v41_rt_die_l20_c8.sv'
    die.write_text('module ot_chip_v41x_die_owner_safe_c8 #(\n    parameter integer C8_PUBLICATION=0,\nparameter X=0)();\not_w15_rom_oneshot_die_px #(.N(4)) u_coll();\nendmodule\n')
    top.write_text('module ot_v41_rt_die_l20_c8 #(\n    parameter integer C8_PUBLICATION=0,\nparameter X=0)();\not_chip_v41x_die_owner_safe_c8 #(.X(X)) dut();\nendmodule\n')
    return [die,top]


def test_repeat_selected_install_reuses_exact_engine(tmp_path):
    inputs=_parent_fixture(tmp_path)
    first=H.install(inputs,tmp_path/'first',enable=True)
    # Simulates Arch's composed source installer carrying a copy from its own
    # pinned checkout. Its exact successor must remain the only definition.
    copied=tmp_path/'engine'/Path(H.ENGINE).name;copied.parent.mkdir()
    copied.write_bytes((ROOT/H.ENGINE).read_bytes())
    sources=[*first['sources'][:-1],copied]
    second=H.install(sources,tmp_path/'second',enable=True)
    assert second['sources'][-1]==copied
    assert len([p for p in second['sources'] if p.name==copied.name])==1
    assert second['verilator_args']==['-GCOLL_HEADREG=1']
    assert second['sources'][0].read_bytes()==first['sources'][0].read_bytes()
    copied.write_bytes(copied.read_bytes()+b'\n// changed\n')
    with pytest.raises(ValueError):H.install(sources,tmp_path/'changed')
    assert not (tmp_path/'changed').exists()


def test_second_output_conflict_does_not_partially_install(tmp_path):
    inputs=_parent_fixture(tmp_path)
    output=tmp_path/'selected';output.mkdir()
    (output/inputs[1].name).write_text('immutable conflicting source')
    with pytest.raises(FileExistsError):H.install(inputs,output)
    assert not (output/inputs[0].name).exists()
