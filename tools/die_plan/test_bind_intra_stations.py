"""tests for the opt-in intra-partition stations (bind_intra_stations.py, asbuilt.land_intra_stations):
python3 -m pytest tools/die_plan/test_bind_intra_stations.py

bind_tiny_lanes, type ta (partitions A0, A1): leaf u_a drives u_b inside the partition (o[7:0] -> i[7:0]); the test copy
adds a 1-bit companion u_a.v -> u_b.v.  Key absent = no station and no record; key on = 2 keep stages per bit of the
net and of its companion, the cycles declared per sink bit (bind verify PASS on both), site rows per stage."""
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
import bind_intra_stations as IS  # noqa: E402

EX = HERE / "examples" / "bind_tiny"
HAVE_YOSYS = bool(os.environ.get("OT_BIND_YOSYS")) or bool(shutil.which("docker"))
needs_yosys = pytest.mark.skipif(not HAVE_YOSYS, reason="no Yosys (OT_BIND_YOSYS) and no docker")

REGS = [[10.0, 20.0], [30.0, 40.0]]
SITES = {"ta": [{"src": "u_a.o+v", "dst": "u_b.i+v", "path_um": 900.0, "regs_um": REGS},
                {"src": "u_b.o", "dst": "u_x.i", "regs_um": []}]}
NET = {"src": "u_a.o", "dst": "u_b.i", "with": [["u_a.v", "u_b.v"]], "stages": 2}


def _src(tmp_path):
    src = tmp_path / "src"
    if src.exists():
        return src
    shutil.copytree(EX, src)
    lv = (src / "leaves.sv").read_text()
    for a, b in (("output reg [7:0] o);", "output reg [7:0] o, output reg v);\n    always @(posedge clk) v <= ^i;"),
                 ("module lf_b (input wire clk, input wire [7:0] i,", "module lf_b (input wire clk, input wire v, input wire [7:0] i,"),
                 ("begin o <= i ^ {id, id}; flt <= &i; end", "begin o <= i ^ {id, id}; flt <= &i ^ v; end")):
        assert lv.count(a) == 1, a
        lv = lv.replace(a, b)
    (src / "leaves.sv").write_text(lv)
    pr = (src / "par.sv").read_text()
    a = ("    wire [7:0] a_o;\n    lf_a #(.ID(K)) u_a (.clk(ck), .rst_n(rst_n), .i(x), .o(a_o));\n"
         "    lf_b u_b (.clk(ck), .i(a_o), .id(id), .o(y), .flt(f));")
    assert pr.count(a) == 1
    pr = pr.replace(a, "    wire [7:0] a_o; wire a_v;\n    lf_a #(.ID(K)) u_a (.clk(ck), .rst_n(rst_n), .i(x), .o(a_o), .v(a_v));\n"
                       "    lf_b u_b (.clk(ck), .v(a_v), .i(a_o), .id(id), .o(y), .flt(f));")
    (src / "par.sv").write_text(pr)
    return src


def _plan(tmp_path, key=None, name="plan.json"):
    p = json.loads((EX / "die_plan_lanes.json").read_text())
    p["asbuilt"]["base"] = str(_src(tmp_path))
    if key is not None:
        p["asbuilt"][IS.KEY] = key
    f = tmp_path / name
    f.write_text(json.dumps(p))
    return f


def _bind(plan, out, *cmds):
    for c in cmds:
        rc = bind.main([c, str(plan), "--out", str(out), "--mem", "4"])
        if rc:
            return rc
    return 0


def _files(out):
    return {str(f.relative_to(out)): f.read_bytes() for f in sorted(Path(out).rglob("*")) if f.is_file()}


def test_config_and_sites():
    assert IS.config({}) is None
    cfg = IS.config({IS.KEY: {"types": ["t[ab]"], "nets": [NET], "sites": SITES}})
    assert IS.selected(cfg, "ta") and not IS.selected(cfg, "tax")
    n = cfg["nets"][0]
    assert n["members"] == [(("u_a", "o"), ("u_b", "i")), (("u_a", "v"), ("u_b", "v"))] and n["stages"] == 2
    rows = IS.type_sites(cfg, "ta")
    assert rows == [(n, REGS)]
    with pytest.raises(ValueError, match="no rows"):
        IS.type_sites(cfg, "tb")                                      # matched type without sites rows
    bad = IS.config({IS.KEY: {"types": ["ta"], "nets": [dict(NET, stages=3)], "sites": SITES}})
    with pytest.raises(ValueError, match="stages 3 != len"):
        IS.type_sites(bad, "ta")
    miss = IS.config({IS.KEY: {"types": ["ta"], "nets": [dict(NET, src="u_b.o", dst="u_a.i")], "sites": SITES}})
    with pytest.raises(ValueError, match="0 sites rows"):
        IS.type_sites(miss, "ta")
    for k in ({"types": [], "nets": [NET], "sites": SITES}, {"types": ["ta"], "nets": [], "sites": SITES},
              {"types": ["ta"], "nets": [NET]}, {"types": ["ta"], "nets": [NET], "sites": SITES, "hop": 1},
              {"types": ["ta"], "nets": [dict(NET, stages=0)], "sites": SITES},
              {"types": ["ta"], "nets": [dict(NET, src="u_a")], "sites": SITES},
              {"types": ["ta"], "nets": [dict(NET, extra=1)], "sites": SITES},
              {"types": ["ta"], "nets": [NET, NET], "sites": SITES}):       # the same load named twice
        with pytest.raises(ValueError):
            IS.config({IS.KEY: k})


def test_sites_file_relative_to_base(tmp_path):
    (tmp_path / "s.json").write_text(json.dumps(SITES))
    cfg = IS.config({IS.KEY: {"types": ["ta"], "nets": [NET], "sites": "s.json"}}, base=str(tmp_path))
    assert IS.type_sites(cfg, "ta")[0][1] == REGS
    with pytest.raises(ValueError, match="cannot read"):
        IS.config({IS.KEY: {"types": ["ta"], "nets": [NET], "sites": "nope.json"}}, base=str(tmp_path))


def test_site_rows():
    assert IS.site_rows("u_lis2_u_r0__flt_bank_i_3", REGS) == {"u_lis2_u_r0__flt_bank_i_3.r[0]": [10.0, 20.0],
                                                               "u_lis2_u_r0__flt_bank_i_3.q": [30.0, 40.0]}
    assert IS.site_rows("u_x", [[1.0, 2.0]]) == {"u_x.q": [1.0, 2.0]}
    assert IS.leaf_match("u_r0", "u_r0", "u_u_r0") and IS.leaf_match("u_u_r0", "u_r0", "u_u_r0")
    assert not IS.leaf_match("u_r1", "u_r0", "u_u_r0")


@needs_yosys
def test_key_absent_no_change_and_key_on_stations(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_HCPARAM_ALL", "0")     # the tiny cores have no signed parameter record (unrelated gate)
    base, on = tmp_path / "base", tmp_path / "on"
    assert _bind(_plan(tmp_path), base, "elab", "bind", "verify") == 0
    key = {"types": ["ta"], "nets": [NET], "sites": SITES}
    assert _bind(_plan(tmp_path, key, "plan_on.json"), on, "elab", "bind", "verify") == 0
    fb, fo = _files(base), _files(on)
    assert "bind_intra_stations.json" not in fb and "ot_dp_dly_keep" not in fb["rtl/bind_cells.sv"].decode()
    assert "lis2_" not in fb["rtl/bt_ta.sv"].decode()
    rtl = fo["rtl/bt_ta.sv"].decode()
    st = re.findall(r"ot_dp_dly_keep #\(\.W\(1\), \.D\((\d+)\)\) u_(lis\w+) \(\.clk\(clk\), \.d\((\S+?)\), \.q\((\w+)\)\);", rtl)
    assert len(st) == 9 and {d for d, *_ in st} == {"2"}
    names = {nm for _d, nm, _s, _q in st}
    assert names == {f"lis2_u_b_i_{i}" for i in range(8)} | {"lis2_u_b_v_0"}
    for _d, nm, src, _q in st:
        assert rtl.count(f"{nm}[0]") == 1                             # read by the load pin only
        assert re.fullmatch(r"w_u_a_(o\[[0-7]\]|v\[0\])", src)
    assert "module ot_dp_dly_keep" in fo["rtl/bind_cells.sv"].decode()
    # the load pins read the station chains; the driver wire still exists for its other readers
    m = re.search(r"\.i\(([^)]*)\)", rtl[rtl.index("u_u_b ("):])
    assert m and "lis2_u_b_i_7[0]" in m.group(1) and "w_u_a_o" not in m.group(1)
    # declared cycles: per sink bit, every die instance of the type (A0, A1)
    pipe = json.loads(fo["bind_core_input_pipe.json"])
    assert len(pipe) == 18 and set(pipe.values()) == {2}
    assert {k for k in pipe if k.startswith("p0.")} == {f"p0.u_b.i[{i}]" for i in range(8)} | {"p0.u_b.v[0]"}
    assert "bind_core_input_pipe.json" not in fb
    rec = json.loads(fo["bind_intra_stations.json"])
    assert rec["option"] == key and list(rec["types"]) == ["ta"]
    r = rec["types"]["ta"]
    assert r["cells"] == 9 and r["flops"] == 18 and r["stages"] == {"u_a.o->u_b.i": 2}
    assert [(n["src"], n["dst"], n["width"]) for n in r["nets"]] == [("u_a.o", "u_b.i", 8), ("u_a.v", "u_b.v", 1)]
    assert len(r["sites"]) == 18 and r["sites"]["u_lis2_u_b_i_3.r[0]"] == REGS[0] and r["sites"]["u_lis2_u_b_v_0.q"] == REGS[1]
    # the proof traces depth + declared cycles on every sink: PASS, sinks / latency records unchanged
    vb = json.loads(fb["verify_report.json"])
    vo = json.loads(fo["verify_report.json"])
    assert vb["verdict"] == "PASS" and vo["verdict"] == "PASS"
    for k in ("bind_sinks.json", "bind_latency.json", "bus_groups.json"):
        assert fb[k] == fo[k], k
    changed = {k for k in set(fb) | set(fo) if fb.get(k) != fo.get(k)}
    assert all(not k.startswith("rtl/") or k in ("rtl/bt_ta.sv", "rtl/bind_cells.sv") for k in changed), changed


@needs_yosys
def test_verify_counts_the_cycles(tmp_path, monkeypatch):
    """without the declaration the stations are an as-built mismatch: drop the record and verify must fail"""
    monkeypatch.setenv("OT_HCPARAM_ALL", "0")
    on = tmp_path / "on"
    assert _bind(_plan(tmp_path, {"types": ["ta"], "nets": [NET], "sites": SITES}), on, "elab", "bind") == 0
    (on / "bind_core_input_pipe.json").unlink()
    _bind(_plan(tmp_path, {"types": ["ta"], "nets": [NET], "sites": SITES}), on, "verify")
    assert json.loads((on / "verify_report.json").read_text())["verdict"] != "PASS"


@needs_yosys
@pytest.mark.parametrize("key,msg", [
    ({"types": ["ta"], "nets": [dict(NET, stages=3)], "sites": SITES}, "stages 3 != len"),
    ({"types": ["nomatch"], "nets": [NET], "sites": SITES}, "match no bound type"),
    ({"types": ["t[as]"], "nets": [NET], "sites": SITES}, "ts: the sites file has no rows"),
    ({"types": ["ta"], "nets": [{"src": "u_b.o", "dst": "u_a.i", "stages": 2}],
      "sites": {"ta": [{"src": "u_b.o", "dst": "u_a.i", "regs_um": REGS}]}}, "not a direct driver"),
    ({"types": ["ta"], "nets": [{"src": "u_q.o", "dst": "u_b.i", "stages": 2}],
      "sites": {"ta": [{"src": "u_q.o", "dst": "u_b.i", "regs_um": REGS}]}}, "src leaf u_q"),
])
def test_fail_closed(tmp_path, monkeypatch, capsys, key, msg):
    monkeypatch.setenv("OT_HCPARAM_ALL", "0")
    out = tmp_path / "x"
    rc = _bind(_plan(tmp_path, key), out, "elab", "bind")
    txt = capsys.readouterr()
    rep = out / "bind_report.json"
    errs = json.loads(rep.read_text()).get("errors") if rep.is_file() else []
    assert rc != 0 or errs
    assert msg in txt.out + txt.err + json.dumps(errs), (txt.out[-2000:], txt.err[-2000:])


# ---- OUT-BUS nets (FABLE-FIX-QC-N N4.1): dst "bus:<out bus>" --------------------------------------------------------
BREGS = [[50.0, 60.0]]
BNET = {"src": "u_b.o", "dst": "bus:ys_o", "stages": 1}
BSITES = {"ta": [{"src": "u_b.o", "dst": "bus:ys_o", "regs_um": BREGS}]}


def _plan_bus(tmp_path, key, name, price=1):
    """bind_tiny lanes a0s / a1s (A0 / A1 ys_o -> S d0_i / d1_i, 2 cycles); price = cycles the plan adds to both"""
    p = json.loads((EX / "die_plan_lanes.json").read_text())
    p["asbuilt"]["base"] = str(_src(tmp_path))
    if key is not None:
        p["asbuilt"][IS.KEY] = key
    for ln in p["lanes"]:
        if ln["id"] in ("a0s", "a1s") and price:
            ln["fixed_cycles"] = price
            p["latency"]["lanes"][ln["id"]]["cycles"] += price
            p["latency"]["lanes"][ln["id"]]["fixed"] = price
    f = tmp_path / name
    f.write_text(json.dumps(p))
    return f


def test_bus_net_config_and_sites():
    cfg = IS.config({IS.KEY: {"types": ["ta"], "nets": [NET, BNET], "sites": dict(ta=SITES["ta"] + BSITES["ta"])}})
    n = cfg["nets"][1]
    assert n["bus"] == "ys_o" and n["members"] == [(("u_b", "o"), ("bus:", "ys_o"))] and cfg["nets"][0]["bus"] is None
    assert cfg["bus_depth"] == {"ys_o": 1}
    assert IS.type_sites(cfg, "ta")[1] == (n, BREGS)
    assert IS.bus_stage_rows("u_lob_x__u_b__o_3_0", (1.0004, 2)) == {"u_lob_x__u_b__o_3_0.q": [1.0, 2.0]}
    two = [{"src": "u_a.o", "dst": "bus:ys_o", "stages": 1}, {"src": "u_b.o", "dst": "bus:ys_o", "stages": 2}]
    for nets in (two,                                                                   # one bus = one latency
                 [{"src": "u_b.o", "dst": "bus:ys_o", "with": [["u_a.v", "u_b.v"]], "stages": 1}],  # mixed companions
                 [{"src": "u_b.o", "dst": "bus:ys_o", "with": [["u_a.v", "bus:y_o"]], "stages": 1}],  # two buses
                 [{"src": "u_b.o", "dst": "bus:", "stages": 1}], [BNET, BNET]):
        with pytest.raises(ValueError):
            IS.config({IS.KEY: {"types": ["ta"], "nets": nets, "sites": BSITES}})


@needs_yosys
def test_bus_net_stations_are_lane_cycles(tmp_path, monkeypatch):
    """u_b.o -> u_bout_ys_o gets one station per bit; the lane (priced +1 in the plan) carries it as a source cycle:
    the receiver gets no pad, LATCHECK counts the u_lob_ chain, the proof passes at the priced depth"""
    monkeypatch.setenv("OT_HCPARAM_ALL", "0")
    base, on = tmp_path / "base", tmp_path / "on"
    key = {"types": ["ta"], "nets": [BNET], "sites": BSITES}
    assert _bind(_plan_bus(tmp_path, None, "plan_b0.json", price=0), base, "elab", "bind", "verify") == 0
    assert _bind(_plan_bus(tmp_path, key, "plan_b1.json"), on, "elab", "bind", "verify") == 0
    rtl_b, rtl = (base / "rtl" / "bt_ta.sv").read_text(), (on / "rtl" / "bt_ta.sv").read_text()
    st = re.findall(r"ot_dp_dly_keep #\(\.W\(1\), \.D\(1\)\) u_(lob_\w+) \(\.clk\(clk\), \.d\((\S+?)\), \.q\((\w+)\)\);", rtl)
    assert sorted(nm for nm, _s, _q in st) == sorted(f"lob_ys_o__u_b__o_{i}_0" for i in range(8))
    assert all(re.fullmatch(r"w_u_b_o\[[0-7]\]", src) for _n, src, _q in st) and "lob_" not in rtl_b
    bout = re.search(r"u_bout_ys_o \(.*?\.d\(([^)]*)\)", rtl).group(1)
    assert all(f"lob_ys_o__u_b__o_{i}_0[0]" in bout for i in range(8)) and "w_u_b" not in bout
    # the other out bus of the same leaf output keeps its direct register; the receiver lands no pad for the new cycle
    assert re.search(r"u_bout_y_o \(.*?\.d\(([^)]*)\)", rtl).group(1) == re.search(r"u_bout_y_o \(.*?\.d\(([^)]*)\)", rtl_b).group(1)
    assert "u_lpad_" not in (on / "rtl" / "bt_ts.sv").read_text()
    rec = json.loads((on / "bind_intra_stations.json").read_text())["types"]["ta"]
    assert rec["out_bus"] == {"ys_o": 1} and rec["cells"] == 8 and rec["flops"] == 8
    assert rec["nets"][0]["dst"] == "bus:ys_o" and rec["nets"][0]["width"] == 8
    assert rec["sites"] == {f"u_lob_ys_o__u_b__o_{i}_0.q": BREGS[0] for i in range(8)}
    assert not (on / "bind_core_input_pipe.json").exists()             # lane cycles, not core-input cycles
    lat = {r["lane"]: r for r in json.loads((on / "bind_latency.json").read_text())["buses"]}
    assert lat["a0s"]["bound_cycles"] == 3 if "bound_cycles" in lat["a0s"] else True
    sb = json.loads((base / "bind_sinks.json").read_text())
    so = json.loads((on / "bind_sinks.json").read_text())
    assert sb["snk.d0[3]"][2] + 1 == so["snk.d0[3]"][2] and sb["snk.d0[3]"][:2] == so["snk.d0[3]"][:2]
    assert json.loads((on / "verify_report.json").read_text())["verdict"] == "PASS"
    rep = json.loads((on / "bind_report.json").read_text())
    assert not rep["errors"]
    la = json.loads((on / "bind_lane_asbuilt.json").read_text())
    rows = {r["lane"]: r for r in la["lanes"]}
    assert rows["a0s"]["verdict"] == "PASS" and rows["a0s"]["source"]["bound_lob"] == 1 and rows["a0s"]["delivered"] == 3


@needs_yosys
@pytest.mark.parametrize("key,price,msg", [
    ({"types": ["ta"], "nets": [BNET], "sites": BSITES}, 0, "LAND_INTRA_LATENCY a0s"),          # plan does not price it
    ({"types": ["ta"], "nets": [{"src": "u_a.o", "dst": "bus:ys_o", "stages": 1}],
      "sites": {"ta": [{"src": "u_a.o", "dst": "bus:ys_o", "regs_um": BREGS}]}}, 1, "feeds no bit of out bus ys_o"),
    ({"types": ["ta"], "nets": [{"src": "u_b.o", "dst": "bus:nope_o", "stages": 1}],
      "sites": {"ta": [{"src": "u_b.o", "dst": "bus:nope_o", "regs_um": BREGS}]}}, 1, "no plain out bus nope_o"),
])
def test_bus_net_fail_closed(tmp_path, monkeypatch, capsys, key, price, msg):
    monkeypatch.setenv("OT_HCPARAM_ALL", "0")
    out = tmp_path / "x"
    rc = _bind(_plan_bus(tmp_path, key, "plan_bx.json", price=price), out, "elab", "bind")
    txt = capsys.readouterr()
    rep = out / "bind_report.json"
    errs = json.loads(rep.read_text()).get("errors") if rep.is_file() else []
    assert rc != 0 or errs
    assert msg in txt.out + txt.err + json.dumps(errs), (txt.out[-2000:], txt.err[-2000:])
