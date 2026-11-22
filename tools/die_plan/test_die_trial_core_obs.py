from pathlib import Path
from types import SimpleNamespace
import sys

import pytest
sys.path.insert(0,str(Path(__file__).parent))
import die_trial as D
import gen_phys as G

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


@pytest.mark.parametrize(
    ("offset", "expected"),
    [
        ([0.0, 0.0], (1624.32, 267.84)),
        ([-4.212, 2.172], (1620.108, 270.012)),
    ],
)
def test_core_obs_matches_generated_hard_macro_location(tmp_path, offset, expected):
    lef = tmp_path / "memory.lef"
    lef.write_text("MACRO memory\n  OBS\n    LAYER M4 ;\n      RECT 0 0 1 1 ;\n  END\nEND memory\n")
    core = dict(
        inst="u_memory", module="memory", lef=str(lef), origin_um=[1624.32, 267.84],
        outline_um=[178.632, 81.0], track_offset_um=offset,
    )
    part = dict(hard_cores=[core])
    plan = SimpleNamespace(types={"serdes": part})

    (macro,) = G.type_macros(plan, "serdes", root=tmp_path)
    assert macro[4:6] == pytest.approx(expected)
    x0, y0, x1, y1, layer, module, has_view = D.core_obs(part)[0]
    assert (x0, y0) == pytest.approx(macro[4:6])
    assert (x1 - x0, y1 - y0) == pytest.approx(core["outline_um"])
    assert (layer, module, has_view) == ("M4", "memory", True)
