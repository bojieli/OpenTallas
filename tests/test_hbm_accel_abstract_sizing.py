import importlib.util
from pathlib import Path
import pytest

P=Path(__file__).resolve().parents[1]/'tools/hbm_accel_abstract_sizing.py'
spec=importlib.util.spec_from_file_location('ha9',P)
M=importlib.util.module_from_spec(spec); spec.loader.exec_module(M)


def test_tile_rounds_capacity_up_and_encloses_every_macro():
    m=dict(capacity_bits=256,width_um=3,height_um=2,
           spec={'ports':'1r1w'},clk_to_q_ps={'ss':70},read_energy_fj_tt=1)
    t=M.sram_tile(m,65,2,1.31)
    assert t['macros_per_die']==2
    assert t['capacity_bytes_per_die']==64
    assert t['columns']*t['rows']>=2
    assert t['abstract_area_mm2_per_die']>=t['packed_area_mm2_per_die']
    assert t['qualification'] is False


def test_replacement_does_not_double_charge_legacy_fabric():
    assert M.replacement_die(20,.9,0)==340.5
    assert M.replacement_die(20,1,3)==345.5


@pytest.mark.parametrize('ports,area,extra',[(0,1,0),(20,float('nan'),0),(20,1,-1),(20,1,float('inf'))])
def test_refuse_invalid_owner_area(ports,area,extra):
    with pytest.raises(ValueError): M.replacement_die(ports,area,extra)


def test_default_never_selects_or_qualifies_missing_owner_inputs():
    r=M.report()
    assert not r['physical_launch_allowed']
    assert r['DS']['replacement_die_mm2'] is None
    for q in r['Qwen']:
        assert q['selected_macro'] is None and q['port_fit'] is None
        assert len(q['alternatives'])==4
        assert all(x['qualification'] is False for x in q['alternatives'])


def test_dram_is_total_stack_silicon_not_logic_or_package_area():
    r=M.report(ha2={'ports':20,'per_port_mm2':.9,'additional_service_mm2':0})
    lo,hi=r['DS']['total_silicon_mm2_assumed_DRAM_range']
    assert lo==96*340.5+384*900
    assert hi==96*340.5+384*1450
