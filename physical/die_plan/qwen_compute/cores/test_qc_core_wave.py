"""DIE-QC-57b: qc_core_wave.py views / su_lane_repin.py on a synthetic plan (no kit generation)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import qc_core_wave as W  # noqa: E402
import su_lane_repin as R  # noqa: E402


def _table(n_out=300):
    pins = [dict(name=f"c_i[{i}]", layer="M4", x=0.096, y=round(60.024 + 0.144 * i, 4)) for i in range(760)]
    pins += [dict(name=f"c_o[{j}]", layer="M5", x=round(100.008 + 0.144 * j, 4), y=0.096) for j in range(n_out)]
    return dict(schema="opentallas.core_pins.v1", core=R.BASE, pins=pins)


def _plan(tmp, tbl):
    (tmp / "cores").mkdir()
    (tmp / "cores" / "t1.json").write_text(json.dumps(tbl))
    (tmp / "cores" / "t2.json").write_text(json.dumps(dict(pins=[])))
    plan = dict(partition_types=dict(
        slw_su_l0=dict(hard_cores=[dict(inst="u_lane1", module=R.BASE, outline_um=[414.72, 267.84],
                                        pins_file="cores/t1.json")]),
        other=dict(hard_cores=[dict(inst="u_x", module="qfd_other", outline_um=[10, 10], pins_file="cores/t2.json"),
                               dict(inst="u_y", module="qfd_signed", outline_um=[10, 10], pins_file="cores/t2.json",
                                    lef="x.lef")])))
    (tmp / "plan.json").write_text(json.dumps(plan) + "\n")
    return tmp / "plan.json"


def test_repin_and_views(tmp_path):
    p = _plan(tmp_path, _table())
    rtl = tmp_path / "rtl/physical"
    rtl.mkdir(parents=True)
    (rtl / f"{R.BASE}_l1.sv").write_text(f"module {R.BASE}_l1 (input wire clk, input wire rst_n,\n"
                                         "    input wire [759:0] c_i, output wire [247:0] c_o);\nendmodule\n")
    assert R.main(["--plan", str(p), "--rtl-dir", str(rtl), "--write"]) == 0
    plan = json.loads(p.read_text())
    assert plan["partition_types"]["slw_su_l0"]["hard_cores"][0]["module"] == f"{R.BASE}_l1"
    pins = json.loads((tmp_path / "cores/t1.json").read_text())["pins"]
    names = [q["name"] for q in pins]
    assert len(pins) == 760 + 248 + 2 and names[-2:] == ["clk", "rst_n"]
    assert all(q["dir"] in ("in", "out") for q in pins)
    for q in pins:   # every pin on the kit track phase (0.012 + 0.048 k)
        c = q["y"] if q["layer"] == "M4" else q["x"]
        assert abs((c - 0.012) / 0.048 - round((c - 0.012) / 0.048)) < 1e-6, q
    s = [q["x"] for q in pins if q["layer"] == "M5"]
    assert len(set(s)) == len(s)
    v = W.plan_views(str(p), repo=tmp_path)
    assert [x["module"] for x in v["view_list"]] == [f"{R.BASE}_l1"]
    assert v["view_list"][0]["family"] == "su_lane"
    assert [x["module"] for x in v["no_recipe"]] == ["qfd_other"]


def test_repin_refuses_short_table(tmp_path):
    p = _plan(tmp_path, _table(n_out=100))
    rtl = tmp_path / "rtl/physical"
    rtl.mkdir(parents=True)
    (rtl / f"{R.BASE}_l1.sv").write_text(f"module {R.BASE}_l1 (input wire clk, input wire rst_n,\n"
                                         "    input wire [759:0] c_i, output wire [247:0] c_o);\nendmodule\n")
    try:
        R.main(["--plan", str(p), "--rtl-dir", str(rtl)])
    except SystemExit as e:
        assert "output slots 100" in str(e)
    else:
        raise AssertionError("short table accepted")
