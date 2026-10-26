"""Unit tests for pushdown.py (wrapper / pins / contract / check / die) on the synthetic spec in testdata/.
    python3 -m pytest -q tools/die_feedthrough/test_pushdown.py
"""
import copy
import re
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pushdown as pd  # noqa: E402

TD = HERE / "testdata"
SPEC = pd.load_spec(TD / "ftspec_example.json")
KIT_V = (TD / "kit_top.sv").read_text()
LAYERS = pd.load_layers()
REPO = HERE.parent.parent
GLUE = "rtl/dsrom_sys/s81_glue/"


def wrap(spec=SPEC, **kw):
    return pd.gen_wrapper(spec, "blk_m", pd.parse_kit_ports_verilog(KIT_V, "blk_m"), **kw)


# ------------------------------------------------------------------ wrapper
def test_parse_kit_ports_ansi_with_params_and_continuation():
    ps = pd.parse_kit_ports_verilog(KIT_V, "blk_m")
    assert [(p["name"], p["dir"], p["range"]) for p in ps] == [
        ("rst_n", "input", ""), ("x", "input", "[15:0]"), ("xk2", "input", "[15:0]"), ("ck_r0", "input", ""),
        ("xo", "output", "[15:0]"), ("xok", "output", "[3:0]")]
    js = pd.parse_kit_ports_json(json.loads((TD / "kit_ports.json").read_text()))
    assert [p["range"] for p in js] == ["", "", "[7:0]", "[7:0]"]


def test_wrapper_structure():
    v, side = wrap(station="ft_pipe_reg")
    assert "module blk_m__ft0a1b2c3d (" in v and "blk_m u_kit (" in v
    for p in ("rst_n", "x", "xk2", "ck_r0", "xo", "xok"):
        assert f".{p}({p})" in v
    for k, n in ((0, 2), (1, 1), (2, 2)):
        for j in range(n):
            assert f" ft{k}_s{j} (" in v
        assert f"input wire ft{k}_ck_i" in v and f"output wire ft{k}_ck_o" in v
    assert "ft0_s1 (.ck(ft0_ck1)" in v          # forwarded clock chained station to station
    assert "module ft_pipe_reg" in v and "posedge ck" in v and not re.search(r"\b(valid|ready)\w*\s*\(", v)
    assert side["reset"] == "rst_n" and side["block_clock"] == "ck_r0"
    assert side["paths"][0]["rep_sites"] == [[100.0, 41.0]]
    assert [r["inst"] for r in side["paths"][2]["regs"]] == ["ft2_s0", "ft2_s1"]


def test_wrapper_block_clock_and_errors():
    sp = copy.deepcopy(SPEC)
    sp["clock"] = "block"
    v, _ = wrap(sp, station="ot_dvrly_st", hc=1)
    assert "ot_dvrly_st #(.W(8), .HC(1)) ft0_s0 (.ck(ck_r0), .rs(rst_n)" in v and "ft0_ck_i" not in v
    bad = copy.deepcopy(SPEC)
    bad["ports"][0]["name"] = "x"
    bad["paths"][0]["in"] = "x"
    with pytest.raises(ValueError, match="collide"):
        wrap(bad)
    with pytest.raises(ValueError, match="not a kit input"):
        wrap(sp, clock="nope")


def _iverilog(files, top, tmp, tb=None):
    out = tmp / "a.out"
    r = subprocess.run(["iverilog", "-g2012", "-s", top, "-o", str(out)] + [str(f) for f in files],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    if tb:
        r = subprocess.run(["vvp", str(out)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        return r.stdout
    return ""


@pytest.mark.skipif(not shutil.which("iverilog"), reason="iverilog not installed")
def test_wrapper_compiles_and_pipes(tmp_path):
    v, _ = wrap(station="ft_pipe_reg")
    (tmp_path / "w.v").write_text(v)
    tb = """module tb;
  reg ck = 0, rst_n = 0; reg [7:0] d = 0; wire [7:0] q; integer t; reg [7:0] hist [0:15];
  blk_m__ft0a1b2c3d dut (.rst_n(rst_n), .x(16'd0), .xk2(16'd0), .ck_r0(ck), .xo(), .xok(),
    .ft0_i(d), .ft0_o(q), .ft1_i(4'd0), .ft1_o(), .ft2_i(3'd0), .ft2_o(),
    .ft0_ck_i(ck), .ft0_ck_o(), .ft1_ck_i(ck), .ft1_ck_o(), .ft2_ck_i(ck), .ft2_ck_o());
  initial begin
    for (t = 0; t < 12; t = t + 1) begin
      d = 8'h11 * t + 3; hist[t] = d; #1 ck = 1; #1 ck = 0;
      if (t >= 2 && q !== hist[t - 1]) begin $display("FAIL t=%0d q=%h want %h", t, q, hist[t - 1]); $finish; end
    end
    $display("PASS"); $finish;
  end
endmodule
"""
    (tmp_path / "tb.v").write_text(tb)
    out = _iverilog([tmp_path / "w.v", TD / "kit_top.sv", tmp_path / "tb.v"], "tb", tmp_path, tb=True)
    # q after the edge of cycle t holds d of cycle t-1: two stages, sampled after the 2nd edge -> d(t-1)
    assert "PASS" in out, out


@pytest.mark.skipif(not shutil.which("verilator"), reason="verilator not installed")
def test_wrapper_verilator_lint(tmp_path):
    v, _ = wrap(station="ft_pipe_reg")
    (tmp_path / "w.v").write_text(v)
    r = subprocess.run(["verilator", "--lint-only", "-Wall", "-Wno-DECLFILENAME", "-Wno-UNUSED", "--top-module",
                        "blk_m__ft0a1b2c3d", str(tmp_path / "w.v"), str(TD / "kit_top.sv")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


@pytest.mark.skipif(not shutil.which("iverilog"), reason="iverilog not installed")
def test_wrapper_with_real_station(tmp_path):
    files = []
    for f in ("dsfd_rly_masters_dvh.sv", "dsfd_rly_masters_dv276.sv", "ot_s81_rly.sv"):
        r = subprocess.run(["git", "-C", str(REPO), "show", f"origin/main:{GLUE}{f}"], capture_output=True, text=True)
        if r.returncode != 0:
            pytest.skip("origin/main relay RTL not available")
        (tmp_path / f).write_text(r.stdout)
        files.append(tmp_path / f)
    v, _ = wrap(station="ot_dvrly_st", hc=1)
    (tmp_path / "w.v").write_text(v)
    _iverilog([tmp_path / "w.v", TD / "kit_top.sv"] + files, "blk_m__ft0a1b2c3d", tmp_path)


# ------------------------------------------------------------------ pins
def _on_grid(v, lay):
    k = (v - lay["offset"]) / lay["pitch"]
    return abs(k - round(k)) < 1e-6


def test_pin_offsets_grid_and_errors():
    o = pd.pin_offsets(40.0, 42.0, 8, 0.08, 0.116)
    assert len(o) == 8 and all(40.0 <= x <= 42.0 for x in o)
    steps = {round((b - a) / 0.08, 6) for a, b in zip(o, o[1:])}
    assert len(steps) == 1 and float(steps.pop()).is_integer()
    with pytest.raises(ValueError):
        pd.pin_offsets(0.0, 0.5, 10, 0.08)


def test_pins_on_grid_in_range_and_aligned():
    pl = pd.place_ports(SPEC, LAYERS)
    ports = {p["name"]: p for p in pd.ft_ports(SPEC)}
    assert len({p["pin"] for p in pl}) == len(pl) == sum(p["bits"] for p in ports.values())
    W, H = SPEC["outline"]
    for p in pl:
        lay = LAYERS[p["layer"]]
        assert _on_grid(p["offset"], lay), p
        sp = ports[p["port"]] if ports[p["port"]]["role"] == "data" else ports[ports[p["port"]]["data_port"]]
        assert sp["lo"] <= p["offset"] <= sp["hi"]
        x, y = p["location"]
        assert {"W": x < 1, "E": x > W - 1, "S": y < 1, "N": y > H - 1}[p["face"]]
    off = {p["pin"]: p["offset"] for p in pl}
    for b in range(8):   # straight path: in and out bits on the same tracks
        assert off[f"ft0_i[{b}]"] == off[f"ft0_o[{b}]"]
    assert off["ft0_ck_i"] == off["ft0_ck_o"]
    assert off["ft0_i[3]"] < off["ft0_ck_i"] < off["ft0_i[4]"]   # clock in the middle slot


def test_pins_tcl_and_hints():
    tcl, js = pd.gen_pins(SPEC, LAYERS)
    assert "place_pin -pin_name {ft0_i[0]} -layer M8 -location {" in tcl
    assert "place_pin -pin_name {ft1_o[3]} -layer M9" in tcl
    hints = {h["inst"]: h for h in js["reg_hints"]}
    assert hints["ft2_s0"]["horiz"] and not hints["ft2_s1"]["horiz"]   # L path: 2nd register on the N leg
    assert all(ln.startswith("#") for ln in tcl.splitlines() if "ft_place_stage" in ln)


# ------------------------------------------------------------------ contract
def test_contract_fence_complements_corridors():
    tcl, js, audit = pd.gen_contract(SPEC)
    W, H = SPEC["outline"]
    corr, fence = js["corridors"], js["fence"]
    a_c = pd.union_area(corr)
    a_f = sum((r[2] - r[0]) * (r[3] - r[1]) for r in fence)
    assert math.isclose(a_c + a_f, W * H, rel_tol=1e-6)
    assert math.isclose(pd.union_area(fence), a_f, rel_tol=1e-9)   # fence rects disjoint
    for f in fence:
        for c in corr:
            assert min(f[2], c[2]) - max(f[0], c[0]) <= 1e-9 or min(f[3], c[3]) - max(f[1], c[1]) <= 1e-9
    assert "set_routing_layers -signal M2-M9" in tcl
    assert tcl.count("set_global_routing_region_adjustment") == 2 * len(fence)
    assert js["signal_max"] == "M7" and js["ft_layers"] == ["M8", "M9"] and "no full-footprint" in js["obs_rule"]
    assert "ft0_i" in js["ft_nets"] and "ft0_ck_o" in js["ft_nets"] and "ft2_s1" in js["ft_insts"]
    assert "proc ft_audit" in audit and "getGuides" in audit


# ------------------------------------------------------------------ check_abstract
def _lef(obs=(), skip=(), layer_override=None, move=None):
    W, H = SPEC["outline"]
    L = ["VERSION 5.8 ;", f"MACRO {SPEC['variant']}", "  CLASS BLOCK ;", "  ORIGIN 0 0 ;", f"  SIZE {W} BY {H} ;"]
    for p in pd.place_ports(SPEC, LAYERS):
        if p["pin"] in skip:
            continue
        x, y = p["location"]
        w, h = p["size"]
        if move == p["pin"]:
            x = 10.0
        lay = (layer_override or {}).get(p["pin"], p["layer"])
        L += [f"  PIN {p['pin']}", "    DIRECTION INPUT ;", "    PORT", f"      LAYER {lay} ;",
              f"        RECT {x - w / 2:.4f} {y - h / 2:.4f} {x + w / 2:.4f} {y + h / 2:.4f} ;", "    END",
              f"  END {p['pin']}"]
    L.append("  OBS")
    L += ["    LAYER M1 ;", f"      RECT 0 0 {W} {H} ;"]   # low-layer blanket is allowed
    for lay, r in obs:
        L += [f"    LAYER {lay} ;", "      RECT " + " ".join(f"{v:.3f}" for v in r) + " ;"]
    L += ["  END", f"END {SPEC['variant']}", "END LIBRARY"]
    return "\n".join(L) + "\n"


def test_check_abstract_pass_and_blanket():
    W, H = SPEC["outline"]
    assert pd.check_abstract(_lef(), SPEC)["ok"]
    r = pd.check_abstract(_lef(obs=[("M8", (0, 0, W, H))]), SPEC)
    assert not r["ok"] and r["cover"]["M8"] == 1.0 and "blanket" in r["fails"][0]
    small = [("M9", (10, 10, 20, 20))]   # 0.4 % of the outline: fine
    assert pd.check_abstract(_lef(obs=small), SPEC)["ok"]


def test_check_abstract_stripes():
    W, H = SPEC["outline"]
    stripes = [("M8", (0, y, W, y + 0.48)) for y in [8.64 * i for i in range(1, 14)]]
    assert not pd.check_abstract(_lef(obs=stripes), SPEC)["ok"]            # 6 % > 5 % without the allowance
    assert pd.check_abstract(_lef(obs=stripes), SPEC, allow_stripes=(0.48, 8.64))["ok"]
    dense = [("M8", (0, y, W, y + 0.48)) for y in [2.0 * i for i in range(1, 50)]]
    assert not pd.check_abstract(_lef(obs=dense), SPEC, allow_stripes=(0.48, 8.64))["ok"]


def test_check_abstract_pin_faults():
    assert "missing" in pd.check_abstract(_lef(skip={"ft0_i[2]"}), SPEC)["fails"][0]
    assert "not on M8" in pd.check_abstract(_lef(layer_override={"ft0_o[1]": "M6"}), SPEC)["fails"][0]
    assert "not on face" in pd.check_abstract(_lef(move="ft1_i[0]"), SPEC)["fails"][0]


# ------------------------------------------------------------------ die ECO
def test_die_eco():
    js, tcl = pd.gen_die_eco(TD, json.loads((TD / "plan_example.json").read_text()), TD / "die_example.v")
    assert js["pushed_lanes"] == 1 and js["relays_deleted"] == 3
    ops = js["ops"]
    dels = {o["inst"] for o in ops if o["op"] == "delete_instance"}
    assert dels == {"u_r0", "u_r1", "u_r2"}                  # keep_channel lane L8 (u_q0) untouched
    dnets = {o["net"] for o in ops if o["op"] == "delete_net"}
    assert {"h01[0]", "h12[7]", "ck1", "ck2"} <= dnets and not dnets & {"ck", "rs_n", "a_x[0]", "c_x[0]", "ck3"}
    con = {(o["net"], o["pin"]) for o in ops if o["op"] == "connect_pin"}
    assert ("a_x[5]", "u_blk/ft0_i[5]") in con and ("c_x[5]", "u_blk/ft0_o[5]") in con
    assert ("ck", "u_blk/ft0_ck_i") in con and ("ck3", "u_blk/ft0_ck_o") in con
    assert "delete_instance {u_r1}" in tcl and "connect_pin {a_x[0]} {u_blk/ft0_i[0]}" in tcl


# ------------------------------------------------------------------ CLI
def test_cli_all(tmp_path):
    s = str(TD / "ftspec_example.json")
    assert pd.main(["wrapper", s, "--kit-top", "blk_m", "--kit-verilog", str(TD / "kit_top.sv"), "--out",
                    str(tmp_path)]) == 0
    assert pd.main(["pins", s, "--out", str(tmp_path)]) == 0
    assert pd.main(["contract", s, "--out", str(tmp_path)]) == 0
    v = SPEC["variant"]
    for f in (f"{v}.v", f"{v}.ft.json", f"{v}.pins.tcl", f"{v}.pins.json", f"{v}.fastroute.tcl",
              f"{v}.contract.json", f"{v}.ft_audit.tcl"):
        assert (tmp_path / f).stat().st_size > 0
    (tmp_path / "x.lef").write_text(_lef())
    assert pd.main(["check", s, "--lef", str(tmp_path / "x.lef")]) == 0
    assert pd.main(["die", str(TD), "--plan", str(TD / "plan_example.json"), "--die-verilog",
                    str(TD / "die_example.v"), "--out", str(tmp_path / "die")]) == 0


def test_forwarded_clock_slot_widens_tight_range():
    sp = copy.deepcopy(SPEC)
    for q in sp["ports"]:
        if q["path"] == 1:
            q["bits"], q["lo"], q["hi"] = 1, 100.0, 100.1   # one M9 track: data + clock need two
    sp["paths"][1]["bits"] = 1
    pl = [p for p in pd.place_ports(sp, LAYERS) if p["pin"] in ("ft1_i", "ft1_ck_i")]
    assert len(pl) == 2 and all(_on_grid(p["offset"], LAYERS["M9"]) for p in pl)
    W, H = sp["outline"]
    lef = ["VERSION 5.8 ;", f"MACRO {sp['variant']}", f"  SIZE {W} BY {H} ;"]
    for p in pd.place_ports(sp, LAYERS):
        x, y = p["location"]
        w, h = p["size"]
        lef += [f"  PIN {p['pin']}", "    PORT", f"      LAYER {p['layer']} ;",
                f"        RECT {x - w / 2:.4f} {y - h / 2:.4f} {x + w / 2:.4f} {y + h / 2:.4f} ;", "    END",
                f"  END {p['pin']}"]
    lef += [f"END {sp['variant']}"]
    assert pd.check_abstract("\n".join(lef) + "\n", sp)["ok"]
