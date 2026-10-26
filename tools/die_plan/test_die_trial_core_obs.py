from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent))
import die_trial as D

def test_unmaterialized_core_preserves_declared_route_cap(monkeypatch):
    monkeypatch.setattr(D,"lef_top_layer",lambda _:None)
    core=dict(origin_um=[2,3],outline_um=[7,11],module="head",obs_max="M7")
    assert D.core_obs({"hard_cores":[core]})==[(2,3,9,14,"M7","head",False)]

def test_unspecified_core_retains_m5_default(monkeypatch):
    monkeypatch.setattr(D,"lef_top_layer",lambda _:None)
    assert D.core_obs({"hard_cores":[dict(origin_um=[0,0],outline_um=[1,2])]})[0][4]=="M5"

def test_real_lef_is_authoritative(monkeypatch):
    monkeypatch.setattr(D,"lef_top_layer",lambda _:"M7")
    assert D.core_obs({"hard_cores":[dict(origin_um=[0,0],outline_um=[1,2],obs_max="M5")]})[0][4]=="M7"
