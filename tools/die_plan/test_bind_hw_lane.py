"""tests for the HBM-HALFWIDTH-2 serialised-lane emitter of tools/die_plan/bind.py:
python3 -m pytest tools/die_plan/test_bind_hw_lane.py

Pure units (hw_lane_spec, HwClasses) always run; the end-to-end binds of the bind_tiny die need Yosys ($OT_BIND_YOSYS or docker)."""
import json
import os
import re
import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind  # noqa: E402

EX = HERE / "examples" / "bind_tiny"
HAVE_YOSYS = bool(os.environ.get("OT_BIND_YOSYS")) or bool(shutil.which("docker"))
needs_yosys = pytest.mark.skipif(not HAVE_YOSYS, reason="no Yosys (OT_BIND_YOSYS) and no docker")


# ---- units -------------------------------------------------------------------------------------------------------
def test_spec_opt_in_only():
    assert bind.hw_lane_spec({"id": "x", "beats": 2, "word_bits": 8}, [5]) is None          # DEC12 lane: untouched
    assert bind.hw_lane_spec({"id": "x"}, [8]) is None


def test_spec_widths():
    s = bind.hw_lane_spec({"id": "x", "hw_lane": True, "beats": 2, "word_bits": 492}, [247, 247])
    assert s == dict(beats=2, word_bits=492, bw=246, bib=1, pw=247, spare=0)
    s = bind.hw_lane_spec({"id": "x", "hw_lane": True, "beats": 4, "word_bits": 601, "beat_index_bits": 2}, [153])
    assert s == dict(beats=4, word_bits=601, bw=151, bib=2, pw=153, spare=1)        # the qq plan counts 2 index bits
    s = bind.hw_lane_spec({"id": "x", "hw_lane": True, "beats": 4, "word_bits": 601, "beat_index_bits": 1}, [152])
    assert s["spare"] == 0


@pytest.mark.parametrize("ln,w", [
    ({"hw_lane": True, "beats": 4, "word_bits": 601}, [152]),          # default bib for 4 beats is 2 -> port must be 153
    ({"hw_lane": True, "beats": 2, "word_bits": 492}, [247, 246]),     # hops disagree
    ({"hw_lane": True, "beats": 3, "word_bits": 9}, [4]),              # 3 beats not supported
    ({"hw_lane": True, "beats": 2}, [5]),                              # no word_bits
])
def test_spec_errors(ln, w):
    with pytest.raises(bind.BindError):
        bind.hw_lane_spec(dict(ln, id="x"), w)


def test_classes_rules(tmp_path):
    f = tmp_path / "c.json"
    f.write_text(json.dumps(dict(default="error", rules=[
        dict(leaf=r"vmb_\w+", port="rr0", bits=[[256, 256]], **{"class": "control"}),
        dict(leaf=r"vmb_\w+", port="rr0", bits=[[0, 255]], **{"class": "payload"}),
        dict(leaf=r"x", port="q", bits={"every": 4, "at": [0, 3]}, **{"class": "level"})])))
    c = bind.HwClasses(f)
    assert c.of("vmb_NW4", "rr0", 256) == "control" and c.of("vmb_NW4", "rr0", 7) == "payload"
    assert c.of("vmb_NW4", "rr1", 7) is None and c.of("wmb_NW4", "rr0", 7) is None
    assert [c.of("x", "q", i) for i in range(5)] == ["level", None, None, "level", "level"]


# ---- end to end on bind_tiny -------------------------------------------------------------------------------------
def tiny(tmp_path, hw, bib=1):
    p = json.loads((EX / "die_plan_lanes.json").read_text())
    p["asbuilt"]["base"] = str(EX)
    if hw:
        pw = 4 + bib
        for l in p["lanes"]:
            if l["id"] == "a0s":
                l.update(hw_lane=True, beats=2, word_bits=8, beat_index_bits=bib)
        for x in p["ports"]:
            if x["id"] == "a0s__0":
                x["width"] = pw
        for tn, bus in (("ta", "ys_o"), ("ts", "d0_i")):
            for b in p["partition_types"][tn]["buses"]:
                if b["name"] == bus:
                    b["width"] = pw
        cls = tmp_path / "classes.json"
        cls.write_text(json.dumps(dict(default="error", rules=[
            dict(leaf=r".*u_b", port="o", bits=[[0, 0]], **{"class": "control"}),
            dict(leaf=r".*u_b", port="o", bits=[[1, 3]], **{"class": "payload"}),
            dict(leaf=r".*u_b", port="o", bits=[[4, 7]], **{"class": "level"})])))
        p["asbuilt"]["hw_leaf_classes"] = str(cls)
    f = tmp_path / ("hw.json" if hw else "base.json")
    f.write_text(json.dumps(p))
    return f


def bound(tmp_path, hw, bib=1):
    out = tmp_path / ("o_hw" if hw else "o_base")
    plan = tiny(tmp_path, hw, bib)
    for c in ("elab", "bind"):
        rc = bind.main([c, str(plan), "--out", str(out), "--mem", "4"])
        assert rc == 0, c
    return out


def rtl(out):
    return "\n".join(f.read_text() for f in sorted(Path(out, "rtl").glob("*.sv")))


@needs_yosys
def test_no_hw_lane_is_unchanged(tmp_path):
    out = bound(tmp_path, False)
    t = rtl(out)
    assert "ot_hbm_hw_lane" not in t and "ot_bus_gear" not in t
    assert not (out / "bind_hw_lanes.json").exists()
    assert "hw_lanes" not in json.loads((out / "bind_report.json").read_text())


@needs_yosys
@pytest.mark.parametrize("bib", [1, 2])
def test_hw_lane_emitted(tmp_path, bib):
    base = bound(tmp_path, False)
    out = bound(tmp_path, True, bib)
    t = rtl(out)
    pw = 4 + bib
    # TX: serialiser + epoch-only station; RX: deserialiser; the word masks come from the leaf classes
    assert re.search(r"ot_hbm_hw_lane_tx #\(\.W\(8\), \.HW\(1\), \.BEATS\(2\), \.CONTROL_MASK\(8'h1\), \.PAYLOAD_MASK\(8'he\)", t)
    assert re.search(r"ot_hbm_hw_lane_rx #\(\.W\(8\), \.HW\(1\), \.BEATS\(2\), \.CONTROL_MASK\(8'h1\)\)", t)
    assert re.search(rf"output wire \[{pw}:0\] \w*ys_o", t)
    assert len(re.findall(r"ot_dp_st #\(\.W\(1\)\) u_bout_ys_o ", t)) == 1
    assert "module ot_hbm_hw_lane_tx" in (out / "rtl" / "bind_cells.sv").read_text()
    assert "module ot_bus_gear_tx" in (out / "rtl" / "bind_cells.sv").read_text()
    # stage counts / LANE_CYCLES check unchanged: bound stages of the lane equal the unserialised bind, words land beats-1 later
    lat = {b["lane"]: b for b in json.loads((out / "bind_latency.json").read_text())["buses"]}
    lat0 = {b["lane"]: b for b in json.loads((base / "bind_latency.json").read_text())["buses"]}
    assert lat["a0s"]["bound_stages"] == lat0["a0s"]["bound_stages"]
    assert lat["a0s"]["word_cycles"] == lat0["a0s"]["bound_stages"] + 1 and lat["a0s"]["width"] == pw
    assert len(lat["a0s"]["source_bits"]) == 8
    for k in lat:
        if k != "a0s":
            assert lat[k]["bound_stages"] == lat0[k]["bound_stages"]
    rep = json.loads((out / "bind_report.json").read_text())
    assert rep["n_errors"] == 0 and rep["hw_lanes"]["unclassified"] == 0
    row = json.loads((out / "bind_hw_lanes.json").read_text())["lanes"][0]
    assert (row["control_bits"], row["payload_bits"], row["level_bits"], row["spare"]) == (1, 3, 4, bib - 1)
    # every other partition file is byte-identical to the unserialised bind except the two ends of the lane, the die top (port widths) and the cell file
    diff = [f.name for f in sorted(Path(base, "rtl").glob("*.sv")) if f.read_text() != Path(out, "rtl", f.name).read_text()]
    assert sorted(diff) == ['bind_cells.sv', 'bind_tiny_lanes_bound_top.sv', 'bt_ta.sv', 'bt_ts.sv'], diff


@needs_yosys
def test_unclassified_bits_are_an_error(tmp_path):
    plan = tiny(tmp_path, True)
    js = json.loads(plan.read_text())
    cls = Path(js["asbuilt"]["hw_leaf_classes"])
    c = json.loads(cls.read_text())
    c["rules"] = c["rules"][:2]                       # bits 4..7 unclassified
    cls.write_text(json.dumps(c))
    out = tmp_path / "o_err"
    bind.main(["elab", str(plan), "--out", str(out), "--mem", "4"])
    bind.main(["bind", str(plan), "--out", str(out), "--mem", "4"])
    rep = json.loads((out / "bind_report.json").read_text())
    assert any(e.startswith("HW_CLASS a0s: 4 ") for e in rep["errors"]), rep["errors"][:3]
