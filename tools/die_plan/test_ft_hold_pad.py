"""T41-OUTPAD 11-12 (DIE-S81-87; COORD adopt of the slice_station__t41 conservative form): plan clock.ft_hold_pad
{"types": {type: {"in": {slot: N}, "out": {slot: N}}}} puts N kept HB4xp67 per bit (data + epoch) between an ft slot's
input port and station 0 ("in") and/or between its last station and the output port ("out"): gen_rtl.ot_dp_hd, instance
u_hdly_<port bus>, kept dont_touch and counted by the kit hook, refused by relay_bay when a padded output lane would grow.
Absent / 0 = byte-same RTL, cell files and kit hooks."""
import copy
import json
import re
import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind  # noqa: E402
import gen_phys  # noqa: E402
import gen_rtl  # noqa: E402
import relay_bay  # noqa: E402
import schema  # noqa: E402
import test_ft_hop_lockup as T  # noqa: E402

PAIR = json.loads((HERE / "examples" / "s81_pair" / "s81_pair_plan.json").read_text())   # type fa: ft slot fz, 64 b, 4 st


def _raw(pad=None, tn="fa"):
    raw = copy.deepcopy(PAIR)
    if pad is not None:
        raw.setdefault("clock", {})["ft_hold_pad"] = {"types": {tn: pad}}
    return raw


def _wrapper(raw, tn="fa"):
    P = schema.Plan(raw)
    return gen_rtl.wrapper(P, tn, gen_rtl.bus_epochs(P))


def _cells(raw):
    with tempfile.TemporaryDirectory() as d:
        gen_rtl.write_rtl(raw, Path(d), emit_die_top=False)
        return (Path(d) / "ot_dp_cells.sv").read_text()


def test_helpers():
    assert gen_rtl.ft_hold_pad({}, "fa", "fz", "out") == 0 and not gen_rtl.uses_ft_hold_pad({})
    r = _raw({"out": {"fz": 2}})
    assert gen_rtl.ft_hold_pad(r, "fa", "fz", "out") == 2 and gen_rtl.ft_hold_pad(r, "fa", "fz", "in") == 0
    assert gen_rtl.ft_hold_pad(r, "fb", "fz", "out") == 0 and gen_rtl.uses_ft_hold_pad(r)
    assert not gen_rtl.uses_ft_hold_pad(_raw({"out": {"fz": 0}, "in": {}}))


def test_default_off_is_byte_same():
    base, zero, other = _raw(), _raw({"in": {"fz": 0}, "out": {"fz": 0}}), _raw({"out": {"fz": 2}}, tn="fb")
    assert _wrapper(base) == _wrapper(zero) == _wrapper(other)
    assert "ot_dp_hd" not in _wrapper(base) and "u_hdly_" not in _wrapper(base)
    assert "module ot_dp_hd" not in _cells(base) and "module ot_dp_hd" not in _cells(zero)
    for raw in (base, zero):
        assert gen_phys.hold_pad_dont_touch_tcl(schema.Plan(raw), "fa") == ""


def test_schema_accepts_and_bounds():
    jsonschema = pytest.importorskip("jsonschema")
    sch = schema.SCHEMA["properties"]["clock"]["properties"]["ft_hold_pad"]
    jsonschema.validate({"types": {"fa": {"in": {"fz": 8}, "out": {"fz": 1}}}}, sch)
    for bad in ({"types": {"fa": {"out": {"fz": 9}}}}, {"types": {"fa": {"out": {"fz": -1}}}},
                {"types": {"fa": {"mid": {"fz": 1}}}}, {"fa": {"out": {"fz": 1}}}):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, sch)
    on_disk = json.loads((HERE / "die_plan.schema.json").read_text())
    assert on_disk["properties"]["clock"]["properties"]["ft_hold_pad"] == json.loads(json.dumps(sch))


def test_gen_wrapper_pads_out_and_in():
    sv = _wrapper(_raw({"out": {"fz": 2}}))
    ep = gen_rtl.bus_epochs(schema.Plan(_raw())).get(("fa", "fz_o"), True)
    wo = 65 if ep else 64
    assert f"ot_dp_hd #(.W({wo}), .N(2)) u_hdly_fz_o (.a(fz_o_hp), .y(fz_o[{wo - 1}:0]));" in sv
    m = re.search(r"u_ft_fz_s3 \(.*?\.q\(([^)]*)\)", sv)
    assert m and m.group(1) == "fz_o_hp[63:0]"                      # the last station drives the pad, not the port
    assert sv.count("ot_dp_hd") == 1 and "u_hdly_fz_i" not in sv
    sv = _wrapper(_raw({"in": {"fz": 3}, "out": {"fz": 1}}))
    epi = gen_rtl.bus_epochs(schema.Plan(_raw())).get(("fa", "fz_i"), True)
    wi = 65 if epi else 64
    assert f"ot_dp_hd #(.W({wi}), .N(3)) u_hdly_fz_i (.a(fz_i[{wi - 1}:0]), .y(fz_i_hd));" in sv
    m = re.search(r"u_ft_fz_s0 \(.*?\.d\(([^)]*)\)", sv)
    assert m and m.group(1) == "fz_i_hd[63:0]"
    st = lambda s: sorted(re.findall(r"\bu_ft_fz_s(\d+) \(", s))
    assert st(sv) == st(_wrapper(_raw())) == ["0", "1", "2", "3"]          # same 4 stations: cycle-neutral


def test_cells_and_kit_hook():
    raw = _raw({"in": {"fz": 3}, "out": {"fz": 2}})
    cells = _cells(raw)
    assert cells.count("module ot_dp_hd") == 1 and "(* keep *) HB4xp67_ASAP7_75t_R u_hb" in cells
    tcl = gen_phys.hold_pad_dont_touch_tcl(schema.Plan(raw), "fa")
    assert "setDoNotTouch 1" in tcl and "*u_hdly_*" in tcl
    assert "plan expects 320..325" in tcl                          # (3 + 2) x 64 (+5 with the epoch bits)
    assert gen_phys.hold_pad_dont_touch_tcl(schema.Plan(raw), "fb") == ""


def _bind(tmp_path, pad):
    P = json.loads((T.EX / "die_plan_lanes.json").read_text())
    P["partition_types"]["tf"]["ft_slots"][0]["stations"] = 3
    P["latency"]["lanes"]["a0y"].update(cycles=5, stations=3)
    if pad is not None:
        P.setdefault("clock", {})["ft_hold_pad"] = pad
    P["asbuilt"]["base"] = str(T.EX)
    tmp_path.mkdir(parents=True, exist_ok=True)
    pf = tmp_path / "p.json"
    pf.write_text(json.dumps(P))
    out = tmp_path / "o"
    rc = 0
    for c in ("elab", "bind", "verify"):
        rc = bind.main([c, str(pf), "--out", str(out), "--mem", "4"])
        if rc:
            break
    v = json.loads((out / "verify_report.json").read_text())
    assert rc == 0 and v["verdict"] == "PASS" and v["counts"]["mismatched"] == 0, v.get("mismatches", [])[:3]
    return (out / "rtl" / "bt_tf.sv").read_text(), (out / "rtl" / "bind_cells.sv").read_text()


@pytest.mark.skipif(not T.HAVE_YOSYS, reason="no Yosys")
def test_bind_pads_bound_stations_and_absent_key_identical(tmp_path):
    slot = json.loads((T.EX / "die_plan_lanes.json").read_text())["partition_types"]["tf"]["ft_slots"][0]["name"]
    base, bcells = _bind(tmp_path / "a", None)
    other, ocells = _bind(tmp_path / "b", {"types": {"zz": {"out": {slot: 2}}}})
    assert (other, ocells) == (base, bcells) and "ot_dp_hd" not in base and "module ot_dp_hd" not in bcells
    sv, cells = _bind(tmp_path / "c", {"types": {"tf": {"in": {slot: 1}, "out": {slot: 2}}}})
    assert "module ot_dp_hd" in cells
    assert sv.count("ot_dp_hd #(.W(9), .N(2)) u_hdly_y_o (.a(y_o_hp), .y(y_o));") == 1, sv
    assert sv.count("ot_dp_hd #(.W(9), .N(1)) u_hdly_y_i (.a(y_i), .y(y_i_hd));") == 1, sv
    assert re.search(r"u_ft_y_o_0 \(.*?\.d\(y_i_hd\[7:0\]\)", sv) and re.search(r"u_ft_y_o_2 \(.*?\.q\(y_o_hp\[7:0\]\)", sv)
    assert sv.count("ot_dp_st #(.W(8))") == base.count("ot_dp_st #(.W(8))") == 3     # cycle-neutral (verify PASS)


def test_relay_bay_refuses_growing_a_padded_output_lane():
    src = (HERE / "relay_bay.py").read_text()
    assert 'if k2 > k and re.search(rf"\\bu_hdly_{s}_o \\(", rtl):' in src and "FAIL_PREBUILD relay_bay" in src
