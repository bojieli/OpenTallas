"""DIE-QC-97 HOLDFORM-1 11-10: plan bus "hold_hb4": N puts N kept HB4xp67 per bit (data + epoch) in front of the
in-boundary flop (gen_rtl.ot_dp_hd u_hdly_<bus>), the kit keeps them dont_touch, the DONT_USE check exempts exactly
them; absent / 0 = byte-same RTL, cell files and kit hooks."""
import copy
import json
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import adder_map_dontuse as AM  # noqa: E402
import gen_phys  # noqa: E402
import gen_rtl  # noqa: E402
import schema  # noqa: E402

PAIR = json.loads((HERE / "examples" / "s81_pair" / "s81_pair_plan.json").read_text())


def _raw(n=None, bus="x_i", tn="fb"):
    raw = copy.deepcopy(PAIR)
    if n is not None:
        for b in raw["partition_types"][tn]["buses"]:
            if b["name"] == bus:
                b["hold_hb4"] = n
    return raw


def _wrapper(raw, tn="fb"):
    P = schema.Plan(raw)
    return gen_rtl.wrapper(P, tn, gen_rtl.bus_epochs(P))


def test_default_off_is_byte_same():
    base, zero = _raw(), _raw(0)
    assert not gen_rtl.uses_hold_hb4(base) and not gen_rtl.uses_hold_hb4(zero)
    assert _wrapper(base) == _wrapper(zero)
    assert "ot_dp_hd" not in _wrapper(base) and "u_hdly_" not in _wrapper(base)
    for raw in (base, zero):
        P = schema.Plan(raw)
        assert gen_phys.hold_pad_dont_touch_tcl(P, "fb") == "" and gen_phys.hold_pad_dont_touch_tcl(P, "fa") == ""
    with tempfile.TemporaryDirectory() as d:
        gen_rtl.write_rtl(base, Path(d), emit_die_top=False)
        cells = (Path(d) / "ot_dp_cells.sv").read_text()
    assert "module ot_dp_hd" not in cells


def test_schema_accepts_and_bounds():
    spec = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["buses"]["items"]
    assert spec["properties"]["hold_hb4"] == {"type": "integer", "minimum": 0, "maximum": 8}
    assert "hold_hb4" not in spec["required"]                    # opt-in: plans without it validate unchanged
    try:
        import jsonschema
    except ImportError:
        return
    jsonschema.validate(_raw(4), schema.SCHEMA)
    for bad in (-1, 9):
        try:
            jsonschema.validate(_raw(bad), schema.SCHEMA)
        except jsonschema.ValidationError:
            continue
        raise AssertionError(f"hold_hb4 {bad} accepted")


def test_gen_wrapper_pads_data_and_epoch():
    raw = _raw(4)
    assert gen_rtl.uses_hold_hb4(raw) and gen_rtl.hold_hb4(raw["partition_types"]["fb"], "x_i") == 4
    sv = _wrapper(raw)
    ep = gen_rtl.bus_epochs(schema.Plan(raw)).get(("fb", "x_i"), True)
    W = 276 + (1 if ep else 0)
    assert f"ot_dp_hd #(.W({W}), .N(4)) u_hdly_x_i (.a(x_i[{W - 1}:0]), .y(x_i_hd));" in sv
    m = re.search(r"u_bin_x_i \(.*?\.d\(([^)]*)\).*?\.ea\(([^)]*)\)", sv)
    assert m and m.group(1) == "x_i_hd[275:0]"
    if ep:
        assert m.group(2) == "x_i_hd[276]"
    # the other in bus is untouched
    assert "u_hdly_z_i" not in sv and re.search(r"u_bin_z_i \(.*?\.d\(z_i\[63:0\]\)", sv)


def test_cells_and_kit_hook():
    raw = _raw(4)
    with tempfile.TemporaryDirectory() as d:
        gen_rtl.write_rtl(raw, Path(d), emit_die_top=False)
        cells = (Path(d) / "ot_dp_cells.sv").read_text()
    assert cells.count("module ot_dp_hd") == 1 and "(* keep *) HB4xp67_ASAP7_75t_R u_hb" in cells
    assert "`ifdef SYNTHESIS" in gen_rtl.HOLD_CELLS and "assign y = a;" in gen_rtl.HOLD_CELLS   # sim model = wire
    tcl = gen_phys.hold_pad_dont_touch_tcl(schema.Plan(raw), "fb")
    assert "setDoNotTouch 1" in tcl and "*u_hdly_*" in tcl
    assert "plan expects 1104..1108" in tcl                      # 4 x 276 (+4 with the epoch bit)
    assert gen_phys.hold_pad_dont_touch_tcl(schema.Plan(raw), "fa") == ""


def test_dont_use_check_exempts_only_hold_pads(tmp_path):
    net = tmp_path / "n.v"
    net.write_text("module t;\n"
                   "  HB4xp67_ASAP7_75t_R \\u_bound.u_hdly_x_i.g_b[0].g_k[0].u_hb  (.A(a), .Y(b));\n"
                   "  HB4xp67_ASAP7_75t_R \\u_bound.u_core.hold_buf  (.A(a), .Y(c));\n"
                   "  BUFx2_ASAP7_75t_R u_ok (.A(a), .Y(d));\nendmodule\n")
    rep = tmp_path / "r.json"
    rc = AM.main(["check", "--dont-use", "*xp*_ASAP7*", "--netlist", str(net), "--report", str(rep)])
    r = json.loads(rep.read_text())
    assert rc == 1 and r["dont_use_cells"] == {"HB4xp67_ASAP7_75t_R": 1} and r["hold_pad_cells"] == 1
    net.write_text("module t;\n  HB4xp67_ASAP7_75t_R \\u_bound.u_hdly_x_i.g_b[0].g_k[0].u_hb  (.A(a), .Y(b));\nendmodule\n")
    assert AM.main(["check", "--dont-use", "*xp*_ASAP7*", "--netlist", str(net), "--report", str(rep)]) == 0


if __name__ == "__main__":
    for n_, f in sorted(globals().items()):
        if n_.startswith("test_"):
            if "tmp_path" in f.__code__.co_varnames[:f.__code__.co_argcount]:
                with tempfile.TemporaryDirectory() as d:
                    f(Path(d))
            else:
                f()
            print("PASS", n_)
