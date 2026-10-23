"""Unit tests for the die_plan schema, loader and validator.   python3 -m pytest -q tools/die_plan/"""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema  # noqa: E402

EX = json.loads((HERE / "examples" / "tiny_plan.json").read_text())


def errs_of(mut):
    p = copy.deepcopy(EX)
    mut(p)
    return schema.validate(p)


def port(p, pid):
    return next(x for x in p["ports"] if x["id"] == pid)


def test_example_valid():
    assert schema.validate(EX) == []


def test_schema_file_in_sync():
    on_disk = json.loads((HERE / "die_plan.schema.json").read_text())
    assert on_disk == json.loads(json.dumps(schema.SCHEMA)), "run: python3 tools/die_plan/schema.py dump-schema"


def test_jsonschema_agrees():
    try:
        import jsonschema
    except ImportError:
        return
    jsonschema.Draft202012Validator(schema.SCHEMA).validate(EX)


def test_structure_errors():
    assert any("missing 'die'" in e for e in errs_of(lambda p: p.pop("die")))
    assert any("unknown key" in e for e in errs_of(lambda p: p.update(extra=1)))
    assert any("data_reset" in e for e in errs_of(lambda p: p["reset"].update(data_reset=True)))
    assert any("orient" in e for e in errs_of(lambda p: p["partitions"][0].update(orient="R90")))


def test_unbound_bus():
    def m(p):
        p["ports"] = [x for x in p["ports"] if x["id"] != "c1"]
        p["lanes"] = [x for x in p["lanes"] if x["id"] != "cfg12"]
    e = errs_of(m)
    assert any("pm1: bus 'cfg_o' is unbound" in x for x in e)
    assert any("pm2: bus 'cfg_i' is unbound" in x for x in e)


def test_width_dir_layer():
    assert any("width 32 != src bus" in e for e in errs_of(lambda p: port(p, "x0").update(width=32)))
    assert any("needs out" in e for e in errs_of(lambda p: port(p, "x0")["src"].update(bus="r_i")))
    assert any("a E face needs H" in e for e in errs_of(lambda p: port(p, "x0").update(layers=["M7"])))


def test_lane_continuity_and_membership():
    assert any("must pass one ft slot" in e for e in errs_of(lambda p: p["lanes"][1].update(ports=["x0", "c1"])))
    e = errs_of(lambda p: p["lanes"].append(dict(id="dup", ports=["c0"])))
    assert any("port c0: in 2 lanes" in x for x in e)


def test_latency_and_pins():
    P = schema.Plan(EX)
    assert P.lane_latency("x") == dict(cycles=3, stations=2, faces=3, fixed=0)
    assert P.lane_latency("r")["cycles"] == 4
    assert P.lane_latency("cfg01")["cycles"] == 1
    pins = P.port_pins("x0")
    assert len(pins) == 64 and len({b for b, _, _ in pins}) == 64
    for b, ln, c in pins:
        L = P.layers[ln]
        k = (c - L["offset_um"]) / L["pitch_um"]
        assert abs(k - round(k)) < 1e-6 and 400.0 <= c <= 420.0
        assert ln == ("M6" if b % 2 == 0 else "M4")
    rev = schema.pin_positions(dict(port(EX, "x0"), order="lsb_high"), P.layers)
    assert [c for _, _, c in rev if _ == "M6"] == sorted([c for _, ln, c in rev if ln == "M6"], reverse=True)


def test_window_too_small():
    P = schema.Plan(EX)
    try:
        schema.pin_positions(dict(port(EX, "x0"), window_um=[400.0, 401.0]), P.layers)
    except ValueError as e:
        assert "tracks" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_orient_frames():
    p = copy.deepcopy(EX)
    p["partitions"][1]["orient"] = "MY"
    P = schema.Plan(p)
    assert P.type_face("pm1", "E") == "W" and P.type_face("pm1", "N") == "N"
    assert P.to_die("pm1", (0.0, 10.0)) == (1728.0, 10.0)
    assert P.to_type("pm1", P.to_die("pm1", (100.0, 200.0))) == (100.0, 200.0)
