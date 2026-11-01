"""Normal native face S0 cannot be moved by an unused representative hint."""
import copy,json,re
from pathlib import Path
from types import SimpleNamespace
import pytest
import schema as S, check as C, g2, die_hop_scan as D
from test_g2 import PAIR

def tiny(second=686.):
    slot=dict(name='ft',width=1,stations=3,regs_um=[[324.,500.],[second,500.],[900.,500.]])
    P=SimpleNamespace(types={'t':dict(outline_um=[1000.,1000.],ft_slots=[slot])},raw={},ports={},parts={})
    pins={'ft_i':{0:(0.,500.,'W'),1:(0.,500.2,'W')},'ft_o':{0:(1000.,500.,'E'),1:(1000.,500.2,'E'),2:(1000.,500.4,'E')}}
    return P,slot,pins

def test_moved_unused_s0_cannot_hide_685_um_first_hop():
    P,s,pins=tiny()
    assert D.md(s['regs_um'][0],s['regs_um'][1])==362.
    rows=D.first_internal_hops(P,'t',s,pins=pins)
    assert rows==[(0,685.),(1,pytest.approx(685.2))]
    assert len(rows)==2 # output-only epoch is not an invented input

def test_valid_actual_input_positive_and_hint_independence():
    P,s,pins=tiny(350.)
    a=D.first_internal_hops(P,'t',s,pins=pins)
    assert max(d for _,d in a)<405
    s['regs_um'][0]=[999.,999.]
    assert D.first_internal_hops(P,'t',s,pins=pins)==a

def test_exact_native_and_registered_landing_are_not_reinterpreted():
    P,s,pins=tiny()
    assert D.first_internal_hops(P,'t',s,pins=pins,full={'ft':{}})==[]
    P.parts={'p':{'type':'t'}};P.ports={'p0':{'dst':{'part':'p','bus':'ft_i'}}}
    P.raw={'clock':{'landing_network':{'edges':[{'id':'cland_clk__p0'}]}}}
    assert not D.normal_slot(P,'t','ft',full={})
    assert D.first_internal_hops(P,'t',s,pins=pins)==[]

def model():
    raw=copy.deepcopy(PAIR)
    raw['partition_types']['fa']['ft_slots'][0]['regs_um']=[[324.,1500.],[686.,1500.],[1040.,1500.],[1400.,1500.]]
    return S.Plan(raw)

def test_exporter_places_normal_s0_at_input_not_unused_hint(tmp_path):
    P=model();out=g2.part_probe(P,'fa',tmp_path)
    text=(out/'probe.tcl').read_text()
    match=re.search(r'place_inst -name st_fz_0_0 -location \{([\d.]+) ([\d.]+)\}',text)
    assert match
    assert float(match[1])==pytest.approx(4.32) # normal input target, then existing core clip
    assert float(match[1])!=324.
    assert 'st_fz_64_0' in (out/'probe.v').read_text() # existing output-only epoch kept

def test_model_and_macro_sites_use_native_normal_input():
    P=model();_,regs,_=C.lane_geometry(P,'z')
    assert regs[1][0]<2.
    assert regs[1]!=(324.,1500.)
    R=C.Report();summary=C.check_hops(P,R,{'z':C.lane_geometry(P,'z')})
    assert summary[0]['normal_s0_first_hop_um']>=685.
    assert R.errors()
