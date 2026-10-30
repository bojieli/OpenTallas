"""Logical strap declaration must not disappear while physical pin-site planning is pending."""
from pathlib import Path
from types import SimpleNamespace
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import gen_phys as GP
from straps import declared


def test_unsited_count_straps_stay_logical_without_invented_sites():
    t=dict(count_straps=[dict(name="strap_ca_K",width=8),dict(name="strap_ca_pad",width=6)])
    p=SimpleNamespace(types={"t":t})
    assert GP.strap_pin_sites(p,"t")==[]
    assert GP.logical_strap_names(t)==["strap_ca_K","strap_ca_pad"]
    # Neither a clock nor an arbitrary same-prefix port is inferred from the netlist.
    assert GP.logical_strap_names({})==[]


def test_sited_ids_and_count_straps_preserve_prior_names():
    t=dict(id_straps=[dict(name="strap_id",width=1,layer="M5",sites_um=[[4.,5.]])],
           count_straps=[dict(name="strap_ca_K",width=1,layer="M5",sites_um=[[6.,7.]])])
    p=SimpleNamespace(types={"t":t})
    assert GP.logical_strap_names(t)==sorted({n.split("[")[0] for n,*_ in GP.strap_pin_sites(p,"t")})


@pytest.mark.parametrize("rows", [[dict(name="clk",width=1)],
    [dict(name="strap_x",width=1),dict(name="strap_x",width=2)]])
def test_invalid_or_duplicate_logical_declarations_refused(rows):
    with pytest.raises(ValueError): GP.logical_strap_names(dict(count_straps=rows))


def test_unsited_ports_cover_all_declared_bits_and_scalar_shapes():
    t=dict(id_straps=[dict(name="strap_id",width=1)],count_straps=[
        dict(name="strap_ca_K",width=8),dict(name="strap_ca_efall",width=1)])
    assert GP.logical_strap_pin_records(t)==([dict(bus="strap_id",bit=0)]+
        [dict(bus="strap_ca_K",bit=i) for i in range(8)]+[dict(bus="strap_ca_efall",bit=None)])
    assert GP.logical_strap_pin_records({})==[]
    with pytest.raises(ValueError):
        GP.logical_strap_pin_records(dict(count_straps=[dict(name="strap_ca_efall",width=2)]))


def test_port_bind_inventory_adds_logical_bits_without_physical_sites(monkeypatch):
    import infra_rtl
    t=dict(count_straps=[dict(name="strap_ca_K",width=8)])
    p=SimpleNamespace(types={"t":t})
    monkeypatch.setattr(GP,"tap_pins",lambda p,tn:[])
    monkeypatch.setattr(GP,"reset_out_pins",lambda p,tn:[])
    monkeypatch.setattr(infra_rtl,"type_ports",lambda t:[])
    got=GP.port_bind_pin_records(p,"t",[])
    assert got==[dict(bus="strap_ca_K",bit=i) for i in range(8)]
    assert GP.strap_pin_sites(p,"t")==[]
