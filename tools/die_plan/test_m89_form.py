"""X-TIER-OTC 11-11 die-top nets (form d) + AREA PINS, die-agnostic: m89_form transform, schema validate, latency rows
unchanged, area pins, G0 check_m89, station_lint M89_OFF_BAY, RTL stage count unchanged."""
import copy
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check  # noqa: E402
import m89_form  # noqa: E402
import schema  # noqa: E402
import station_lint  # noqa: E402

EX = json.loads((HERE / "examples" / "tiny_plan.json").read_text())


def _area(raw, tn, bus, bay):
    for b in raw["partition_types"][tn]["buses"]:
        if b["name"] == bus:
            for k in ("face", "window_um", "layers"):
                b.pop(k, None)
            b["route"], b["bay_um"] = "m89", bay


def _spec(bays=(([300.0, 380.0, 400.0, 480.0], [0, 1]), ([500.0, 380.0, 600.0, 480.0], [2]))):
    return {"schema": m89_form.SCHEMA,
            "slots": [{"type": "mid", "slot": "fx", "bays": [{"rect_um": r, "stations": s} for r, s in bays]}]}


def _form(spec=None, area=True):
    raw = copy.deepcopy(EX)
    if area:
        _area(raw, "src", "x_o", [760.0, 380.0, 860.0, 480.0])     # lane x ends are AREA PINS
        _area(raw, "sink", "x_i", [4.0, 380.0, 104.0, 480.0])
    return m89_form.transform(raw, spec or _spec())


def test_transform_validates_and_keeps_latency():
    P, rep = _form()
    assert schema.validate(P) == []
    a, b = schema.Plan(EX), schema.Plan(P)
    for lid in a.lanes:
        assert b.lane_latency(lid)["cycles"] == a.lane_latency(lid)["cycles"], lid
    ids = {p["id"]: p for p in P["ports"]}
    assert {"x0", "x1", "x2"} <= set(ids)                         # inter-partition ports keep their ids
    assert all(ids[i]["route"] == "m89" and "face" not in ids[i] for i in ("x0", "x1", "x2"))
    assert rep["ports_added"] == 2                                 # one bay -> bay net in each of pm1, pm2
    x = next(l for l in P["lanes"] if l["id"] == "x")["ports"]
    assert x == ["x0", "x__pm1_fx_b0", "x1", "x__pm2_fx_b0", "x2"]
    assert ids["x__pm1_fx_b0"]["src"] == {"part": "pm1", "bus": "fxb0_o"}
    assert ids["x__pm1_fx_b0"]["dst"] == {"part": "pm1", "bus": "fxb1_i"}
    assert "die_top_signal" in P["die"]["layer_budget"]["die_use"]
    r = next(l for l in P["lanes"] if l["id"] == "r")                # untouched lane / ports unchanged
    assert r == next(l for l in EX["lanes"] if l["id"] == "r")


def test_one_sided_m89_is_refused():
    try:
        _form(area=False)                                          # pa.x_o / pb.x_i stay face buses
    except m89_form.FormError as e:
        assert "face end" in str(e)
    else:
        raise AssertionError("one-sided m89 port accepted")


def test_bay_station_cover_checked():
    try:
        _form(_spec(bays=(([300.0, 380.0, 400.0, 480.0], [0]), ([500.0, 380.0, 600.0, 480.0], [2]))))
    except m89_form.FormError as e:
        assert "do not cover" in str(e)
    else:
        raise AssertionError("missing station accepted")


def test_validate_rejects_face_on_m89_port_and_area_bus_without_bay():
    P, _ = _form()
    q = copy.deepcopy(P)
    next(p for p in q["ports"] if p["id"] == "x1")["face"] = "E"
    assert any("carries no face" in e for e in schema.validate(q))
    q = copy.deepcopy(P)
    next(b for b in q["partition_types"]["src"]["buses"] if b["name"] == "x_o").pop("bay_um")
    assert any("need bay_um" in e for e in schema.validate(q))
    q = copy.deepcopy(P)
    next(p for p in q["ports"] if p["id"] == "x1").pop("route")    # m89 end on a non-m89 port
    assert any("is an m89 end but the port is not route m89" in e for e in schema.validate(q))


def test_area_pins_inside_bay_and_type_pins():
    sites = schema.area_pin_sites([10.0, 20.0, 110.0, 70.0], 65)
    assert len(sites) == 65 and len({(x, y) for _, _, x, y in sites}) == 65
    assert all(10 < x < 110 and 20 < y < 70 and ln == "M7" for _, ln, x, y in sites)
    import gen_phys
    P, _ = _form()
    pins = [p for p in gen_phys.type_pins(schema.Plan(P), "src") if p[0] == "x_o"]
    assert len(pins) == 64 + (1 if schema.has_epoch(next(p for p in P["ports"] if p["id"] == "x0")) else 0)
    assert all(p[5] == schema.AREA_FACE and 760 < p[3] < 860 and 380 < p[4] < 480 for p in pins)


class _R:
    def __init__(self):
        self.errs = []

    def err(self, cls, msg, **k):
        self.errs.append(msg)

    def warn(self, *a, **k):
        pass


def test_check_m89_reach_pins_and_replicas():
    even = _spec(bays=tuple(([x, 380.0, x + 100.0, 480.0], [k]) for k, x in enumerate((100.0, 300.0, 650.0))))
    P, _ = _form(even)                                             # hops <= 350 um, bays clear of the (432, 432) tap
    R = _R()
    out = check.check_m89(schema.Plan(P), R, {})
    assert out["ports"] == 7 and R.errs == [], R.errs
    far = _spec(bays=(([10.0, 380.0, 110.0, 480.0], [0, 1]), ([700.0, 380.0, 800.0, 480.0], [2])))
    P, _ = _form(far)
    R = _R()
    check.check_m89(schema.Plan(P), R, {})
    assert any("bay->bay" in e for e in R.errs)                    # 690-um bay -> bay hop > 405
    tiny = _spec(bays=(([300.0, 380.0, 310.8, 390.8], [0, 1]), ([500.0, 380.0, 600.0, 480.0], [2])))
    P, _ = _form(tiny)
    R = _R()
    check.check_m89(schema.Plan(P), R, {})
    assert any("/gcell" in e for e in R.errs)                      # 128 entry pins on one gcell


def test_station_lint_off_bay():
    P, _ = _form()
    assert not [r for r in station_lint.lint_plan(P) if r["kind"] == "M89_OFF_BAY"]
    s = next(s for s in P["partition_types"]["mid"]["ft_slots"] if s["name"] == "fxb0")
    s["regs_um"][1] = [800.0, 800.0]
    bad = [r for r in station_lint.lint_plan(P) if r["kind"] == "M89_OFF_BAY"]
    assert len(bad) == 1 and bad[0]["name"] == "fxb0" and bad[0]["index"] == 1


def _stages(d):
    return len(re.findall(r"\bot_dp_st\b[^;]*\bu_ft_", (Path(d) / "tiny_mid_part.sv").read_text()))


def test_rtl_same_ft_stations(tmp_path):
    P, _ = _form()
    (tmp_path / "d.json").write_text(json.dumps(P))
    for name, plan in (("base", HERE / "examples" / "tiny_plan.json"), ("d", tmp_path / "d.json")):
        subprocess.run([sys.executable, "-I", str(HERE / "gen.py"), "rtl", str(plan), "--out", str(tmp_path / name)],
                       check=True, capture_output=True)
    assert _stages(tmp_path / "base") == _stages(tmp_path / "d") > 0
    top = (tmp_path / "d" / "tiny_top.sv").read_text()
    assert "x__pm1_fx_b0" in top                                   # the bay -> bay die-top net is a top wire
