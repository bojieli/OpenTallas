import importlib.util
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[2]
path=ROOT/"physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py"
spec=importlib.util.spec_from_file_location("legacy_pin_writer",path)
G=importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)

def test_declared_eng_shape_and_center_preserved():
    q=dict(name="out_res[0]",layer="M5",x=4.812,y=267.744)
    shapes={"out_res[0]":("M5",.024,.192,4.8,267.648,4.824,267.84)}
    out,pw,ph,moved=G.planned_pin_geometry(q,shapes,172.8,267.84)
    assert out==q and (pw,ph,moved)==(.024,.192,0)

def test_inset_access_center_rejected_without_projection():
    q=dict(name="rst_n[0]",layer="M5",x=9.564,y=1.076)
    shapes={"rst_n[0]":("M5",.024,2.121,9.552,.016,9.576,2.137)}
    with pytest.raises(SystemExit,match="no implicit projection"):
        G.planned_pin_geometry(q,shapes,172.8,172.8)
    assert q["y"]==1.076

def test_explicit_repin_edge_uses_standard_shape():
    q=dict(name="data",layer="M5",x=4.812,y=.042)
    out,pw,ph,moved=G.planned_pin_geometry(q,{},172.8,172.8)
    assert out==q and (pw,ph,moved)==(.024,.084,0)

def test_legacy_projection_remains_explicit_opt_out():
    q=dict(name="data",layer="M5",x=4.812,y=1.076)
    out,pw,ph,moved=G.planned_pin_geometry(q,{},172.8,172.8,modern=False)
    assert out["y"]==.042 and moved==1 and q["y"]==1.076

