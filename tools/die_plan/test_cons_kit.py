"""KW-FIX-24/CONSKIT 11-06: opt-in conservative re-kit (OT_CONS_KIT=1 via kit-wave item_env) in gen_phys.write_type_kit.
    python3 -m pytest -q tools/die_plan/test_cons_kit.py"""
import copy
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import schema  # noqa: E402

TINY = json.loads((HERE / "examples" / "tiny_plan.json").read_text())
CONS_KEYS = ("OT_CONS_KIT", "OT_CONS_UTIL", "OT_CONS_MAX_LAYER", "OT_CONS_PIN_LAYER_ADJ")


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in CONS_KEYS:
        monkeypatch.delenv(k, raising=False)


def _kit(d, util=0.5, **env):
    old = {k: os.environ.get(k) for k in env}
    os.environ.update({k: str(v) for k, v in env.items()})
    try:
        return gen_phys.write_type_kit(schema.Plan(copy.deepcopy(TINY)), "src", d, [], util=util)
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _files(kd):
    return {str(p.relative_to(kd)): p.read_bytes() for p in sorted(Path(kd).rglob("*")) if p.is_file()}


def _cfg(kd):
    return dict(l[len("export "):].split(" = ", 1) for l in (Path(kd) / "config.mk").read_text().splitlines()
                if l.startswith("export ") and " = " in l)


def test_off_by_default_byte_identical():
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        ka, kb = _kit(a), _kit(b, OT_CONS_KIT="0")
        fa, fb = _files(ka), _files(kb)
        assert fa == fb
        assert "cons_kit.json" not in fa and "cons_gpl_pre.tcl" not in fa and "cons_grt_pre.tcl" not in fa
        assert b"OT_CONS" not in fa["config.mk"]


def test_caps_apply_and_pin_floor_holds():
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        base, cons = _cfg(_kit(a)), None
        kd = _kit(b, OT_CONS_KIT="1")
        cons = _cfg(kd)
        top = schema.Plan(copy.deepcopy(TINY)).type_top_layer("src")
        assert base["MAX_ROUTING_LAYER"] == top and base["PLACE_DENSITY"] == "0.5"
        assert cons["PLACE_DENSITY"] == "0.35"
        assert cons["PRE_GLOBAL_PLACE_TCL"] == "/work/cons_gpl_pre.tcl" and (kd / "cons_gpl_pre.tcl").is_file()
        assert "source [file join $cgp_dir face_flops.tcl]" in (kd / "cons_gpl_pre.tcl").read_text()
        rec = json.loads((kd / "cons_kit.json").read_text())
        floor = rec["signal_max_layer"]["pin_floor"]
        io_layers = {l.split(" -layer ")[1].split()[0] for l in (kd / "io.tcl").read_text().splitlines()
                     if l.startswith("place_pin") and " -layer " in l}
        assert floor == max(io_layers, key=lambda x: int(x[1:]))
        # the ceiling is never below a pin layer of the type
        assert int(cons["MAX_ROUTING_LAYER"][1:]) == max(6, int(floor[1:]))
        assert all(int(x[1:]) <= int(cons["MAX_ROUTING_LAYER"][1:]) for x in io_layers)
        if int(floor[1:]) > 6:
            want = [f"M{k}" for k in range(7, int(floor[1:]) + 1)]
            assert cons["OT_CONS_PIN_LAYERS"] == " ".join(want) and cons["OT_CONS_PIN_LAYER_ADJ"] == "0.9"
            assert cons["PRE_GLOBAL_ROUTE_TCL"] == "/work/cons_grt_pre.tcl"
            assert cons["OT_CONS_BASE_PRE_GRT"] == base["PRE_GLOBAL_ROUTE_TCL"]
            assert rec["signal_max_layer"]["pin_access_layers"] == want
        assert cons["OT_CONS_KIT"] == "1" and cons["OT_CONS_SIGNAL_MAX"] == "M6"
        assert rec["place_density"] == {**rec["place_density"], "kit": 0.5, "cap": 0.35, "used": 0.35}
        # nothing else in the config moved
        changed = {k for k in base if base[k] != cons.get(k)}
        assert changed <= {"PLACE_DENSITY", "MAX_ROUTING_LAYER", "PRE_GLOBAL_PLACE_TCL", "PRE_GLOBAL_ROUTE_TCL"}


def test_density_cap_is_min_and_layer_override():
    with tempfile.TemporaryDirectory() as a:
        c = _cfg(_kit(a, util=0.3, OT_CONS_KIT="1", OT_CONS_UTIL="0.4", OT_CONS_MAX_LAYER="M5"))
        assert c["PLACE_DENSITY"] == "0.3"          # min(kit, cap): never raised
        assert c["OT_CONS_SIGNAL_MAX"] == "M5"


def test_ceiling_floors_at_pin_layer(tmp_path):
    cfg = ["export MAX_ROUTING_LAYER = M7", "export PLACE_DENSITY = 0.5",
           "export PRE_GLOBAL_PLACE_TCL = /work/face_flops.tcl", "export PRE_GLOBAL_ROUTE_TCL = /work/hold_repair_pre.tcl"]
    io = "place_pin -pin_name {a[0]} -layer M4 -location {0 1}\nplace_pin -pin_name clk -layer M5 -location {0 2}\n"
    c = list(cfg)
    rec = gen_phys.cons_kit_apply(c, tmp_path, gen_phys.cons_kit_settings({"OT_CONS_KIT": "1"}), io, "M7")
    assert "export MAX_ROUTING_LAYER = M6" in c and rec["signal_max_layer"]["pin_access_layers"] == []
    assert "export PRE_GLOBAL_ROUTE_TCL = /work/hold_repair_pre.tcl" in c   # no pin above M6: no GRT wrapper
    # a macro signal pin on M7 raises the floor; its POWER pin on M8 does not
    (tmp_path / "macros").mkdir()
    (tmp_path / "macros" / "m.lef").write_text(
        "MACRO m\n PIN d\n  USE SIGNAL ;\n  PORT\n   LAYER M7 ;\n   RECT 0 0 1 1 ;\n  END\n END d\n"
        " PIN VDD\n  USE POWER ;\n  PORT\n   LAYER M8 ;\n  END\n END VDD\nEND m\n")
    c = list(cfg)
    rec = gen_phys.cons_kit_apply(c, tmp_path, gen_phys.cons_kit_settings({"OT_CONS_KIT": "1"}), io, "M7",
                                  ["/work/macros/m.lef"])
    assert "export MAX_ROUTING_LAYER = M7" in c and rec["signal_max_layer"]["pin_floor"] == "M7"
    assert "export OT_CONS_PIN_LAYERS = M7" in c and "export OT_CONS_BASE_PRE_GRT = /work/hold_repair_pre.tcl" in c
    # an M8 face pin (face_layers) keeps M8 as the ceiling; never above the kit top
    c = ["export MAX_ROUTING_LAYER = M8"] + cfg[1:]
    rec = gen_phys.cons_kit_apply(c, tmp_path, gen_phys.cons_kit_settings({"OT_CONS_KIT": "1"}),
                                  io + "place_pin -pin_name {f[0]} -layer M8 -location {0 3}\n", "M8")
    assert "export MAX_ROUTING_LAYER = M8" in c and "export OT_CONS_PIN_LAYERS = M7 M8" in c


def test_settings_validation():
    assert gen_phys.cons_kit_settings({}) is None and gen_phys.cons_kit_settings({"OT_CONS_KIT": "0"}) is None
    assert gen_phys.cons_kit_settings({"OT_CONS_KIT": "1"}) == dict(util=0.35, max_layer="M6", pin_layer_adj=0.9)
    for bad in ({"OT_CONS_KIT": "yes"}, {"OT_CONS_KIT": "1", "OT_CONS_UTIL": "1.5"},
                {"OT_CONS_KIT": "1", "OT_CONS_MAX_LAYER": "M1"}, {"OT_CONS_KIT": "1", "OT_CONS_PIN_LAYER_ADJ": "1"}):
        with pytest.raises(ValueError):
            gen_phys.cons_kit_settings(bad)
