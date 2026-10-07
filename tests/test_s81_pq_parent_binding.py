import importlib.util
import json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('pq_parent',ROOT/'tools/s81/pq_parent_binding.py')
P=importlib.util.module_from_spec(spec);spec.loader.exec_module(P)


def test_native_full_width_contract():
    p=P.native_ports(9,11)
    assert p['f_bus']['bits']==1633
    assert sum(v['bits']for v in p.values()if v['owner']=='field_return')==8832
    assert sum(v['bits']for v in p.values()if v['owner']=='VM_write')==6656
    assert not any(n.startswith('rw_')for n in p)
    assert P.boundary_contract()['old_return_is_drop_in'] is False


def test_screen_pin_names_cannot_qualify_native_partition():
    r=P.pin_contract({'o_bus[0]':dict(direction='OUTPUT')},P.native_ports(9,11))
    assert not r['PASS'] and 'f_bus[0]' in r['missing'] and 'o_bus[0]'in r['extra']


def test_direction_and_missing_fault_are_errors():
    ports={'fault':dict(direction='output',bits=1),'r_e':dict(direction='input',bits=2)}
    pins={'fault':dict(direction='INPUT'),'r_e[0]':dict(direction='INPUT')}
    r=P.pin_contract(pins,ports)
    assert r['wrong_direction']==['fault'] and r['missing']==['r_e[1]']


def test_import_real_def_coordinates_and_reject_unplaced():
    r={'pins':['PINS 1 ;\n - r_row\\[12\\] + NET r_row\\[12\\] + DIRECTION INPUT\n + LAYER M4 ( -1 -1 ) ( 1 1 )\n + FIXED ( 479958 80000 ) N ;\nEND PINS\n']}
    p=P.def_pins(r,1000)
    assert p['r_row[12]']['x_um']==479.958
    r['pins'][0]=r['pins'][0].replace('+ FIXED ( 479958 80000 ) N','')
    with pytest.raises(ValueError):P.def_pins(r)


def test_released_mapping_inventory_sizes_real_operand_state():
    for name,count in [('half',120),('full',98)]:
        p=json.loads((ROOT/f'results/uarch/dsrom_s81_pq_parent_20261007/{name}_inventory.json').read_text())
        assert len(p['stages'])==count
        assert max(s['KMAX']for s in p['stages'])==6144
        assert max(s['SAW']for s in p['stages'])==11
        assert max(s['PHW']for s in p['stages'])==9
        assert max(s['operand_storage_bits']for s in p['stages'])==298752
        assert not p['physical_adopted']


def test_generated_partition_keeps_every_native_boundary():
    text=P.wrapper(dict(PHW=9,SAW=11,KMAX=6144))
    for name in P.native_ports(9,11):assert f'.{name}({name})'in text
    assert '.KMAX(6144)'in text and '.R(128)'in text
    assert 'screen_stub'not in text and 'rw_ph'not in text


def test_parent_slot_cannot_steal_existing_corridor():
    m=dict(insts=[],regions=[dict(name='live_trunk',kind='channel',rect=[900,900,2000,2000])])
    with pytest.raises(ValueError,match='live_trunk'):P.reservation(m,(1000,1000))
    assert not m['insts']


def test_parent_slot_retains_production_area_unknown():
    m=dict(insts=[],regions=[])
    r=P.reservation(m,(1000,1000))
    assert len(m['insts'])==1 and m['insts'][0].master=='ot_s81_pq_native_partition'
    assert r['production_mapped_area_um2'] is None and not r['production_fit_qualified']
