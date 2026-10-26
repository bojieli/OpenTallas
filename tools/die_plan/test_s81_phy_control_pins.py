"""Native HBM PHY geometry drives S81 hard clock/reset entries."""
import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import pytest
import gen_phys
import schema as S
import json

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('s81_phy_controls',ROOT/'physical/die_plan/s81/apply_phy_control_pins.py')
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)


def fixture():
    return {'die':{'name':'s81'},'partition_types':{'phy__t1':{
        'hard':True,'module':'s81p_phy__t1','outline_um':[8657.28,1226.88],
        'clock':{'tap_um':[4328.64,613.44],'layer':'M9'},'reset':{'sync_stages':2},
        'contents':[{'inst':'u_phy_hbm','module':M.MODULE,'status':'reuse'}]}}}


def test_exact_native_pins_and_real_kit_macro_origin():
    raw=fixture();report=M.apply(raw,ROOT);t=raw['partition_types']['phy__t1']
    assert t['clock']['tap_um']==[4379.34,1185.744]
    assert t['reset']['tap_um']==[4379.532,1185.744]
    assert t['reset']['sync_stages']==2
    assert report[0]['added_boot_stages']==report[0]['added_data_cycles']==0
    placed=gen_phys.type_macros(SimpleNamespace(types=raw['partition_types']),'phy__t1')
    assert len(placed)==1 and placed[0][4:]==(8.64,8.64,'R0')
    before=copy.deepcopy(raw);M.apply(raw,ROOT);assert raw==before


def test_missing_native_reset_pin_fails_closed(tmp_path):
    text=(ROOT/M.VIEW).read_text().replace('PIN rst_n','PIN rst_bad')
    p=tmp_path/'bad.lef';p.write_text(text)
    with pytest.raises(ValueError,match='rst_n'):M.lef_contract(p)


def test_existing_invalid_origin_not_silently_replaced():
    raw=fixture();raw['partition_types']['phy__t1']['contents'][0]['origin_um']=[0,0]
    with pytest.raises(ValueError,match='halo'):M.apply(raw,ROOT)


def test_native_hard_controls_keep_exact_lef_coordinates_and_soft_default():
    raw=fixture();M.apply(raw,ROOT);t=raw['partition_types']['phy__t1']
    P=SimpleNamespace(types={'phy':t})
    assert gen_phys.tap_points(P,'phy')==[(4379.34,1185.744),(4379.532,1185.744)]
    # Existing soft plans still use the established collision/PG-aware snapping.
    base=json.loads((ROOT/'tools/die_plan/examples/tiny_plan.json').read_text())
    name=next(iter(base['partition_types']));ty=base['partition_types'][name]
    ty.update(hard=False,outline_um=[80,80],clock={'tap_um':[20,20]})
    ty['reset']={'tap_um':[20.192,20]}
    Q=S.Plan(base)
    ck,rs=gen_phys.tap_points(Q,name)
    assert rs!=tuple(ty['reset']['tap_um'])
    assert abs(rs[1]-ck[1])>8
