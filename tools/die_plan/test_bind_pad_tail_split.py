"""tests for the opt-in landing-pad tail split (bind_pad_tail_split.py, asbuilt.land_pad_tail_split):
python3 -m pytest tools/die_plan/test_bind_pad_tail_split.py

bind_tiny_lanes with a sink partition of TWO leaves (u_s0 / u_s1, declared plan hard cores with pin xy) that read the
same bus: 5 bits of d0 ride a 2-cycle lane and get 3 pad stages (test_bind.test_land_align).  Key absent = the bound RTL
and every record are byte-identical to a bind without the option; key on = shared trunk + one tail copy per core, the
same traced depth per sink (bind verify PASS, same bind_sinks / bind_latency)."""
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
import bind_pad_tail_split as TS  # noqa: E402

EX = HERE / "examples" / "bind_tiny"
HAVE_YOSYS = bool(os.environ.get("OT_BIND_YOSYS")) or bool(shutil.which("docker"))
needs_yosys = pytest.mark.skipif(not HAVE_YOSYS, reason="no Yosys (OT_BIND_YOSYS) and no docker")

SPAR = """`timescale 1ns/1ps
module spar (input wire ck, input wire flt, input wire [7:0] a, input wire [7:0] b, output wire [8:0] q0,
             output wire [8:0] q1);
    lf_sink u_s0 (.clk(ck), .flt(flt), .d0(a), .d1(b), .q(q0));
    lf_sink u_s1 (.clk(ck), .flt(flt), .d0(a), .d1(b), .q(q1));
endmodule
"""


def _pins(x0):
    return ([dict(name=f"d0[{i}]", layer="M4", xy=[x0 + i, 10.0]) for i in range(8)]
            + [dict(name=f"d1[{i}]", layer="M4", xy=[x0 + i, 20.0]) for i in range(8)])


def _plan(tmp_path, split, gap=1000.0):
    src = tmp_path / "src"
    if not src.exists():
        shutil.copytree(EX, src)
        die = (src / "die.v").read_text()
        die = die.replace("wire [8:0] sq;", "wire [8:0] sq; wire [8:0] sq1;")
        die = die.replace("lf_sink snk (.clk(ck), .flt(fo), .d0(y0), .d1(y1), .q(sq));",
                          "spar snk (.ck(ck), .flt(fo), .a(y0), .b(y1), .q0(sq), .q1(sq1));")
        assert "spar snk" in die
        (src / "die.v").write_text(die)
        (src / "spar.sv").write_text(SPAR)
    p = json.loads((EX / "die_plan_lanes.json").read_text())
    ab = p["asbuilt"]
    ab["base"] = str(src)
    ab["files"] = ab["files"] + ["spar.sv"]
    ab["dissolve"] = ab["dissolve"] + ["spar"]
    ab["land_align"] = "cell"
    for x in p["ports"]:
        if x["id"] == "a0s__0":
            x["width"] = 5
        if x["id"] == "a1s__0":
            x["width"] = 16
    for b in p["partition_types"]["ta"]["buses"]:
        if b["name"] == "ys_o":
            b["width"] = 16
    ts = p["partition_types"]["ts"]
    for b in ts["buses"]:
        if b["name"] == "d1_i":
            b["width"] = 16
        b["leaf"] = b["leaf"].replace("core.", "u_s0.")
    ts["outline_um"] = [2000.0, 100.0]
    ts["hard_cores"] = [dict(inst="u_s0", module="lf_sink", origin_um=[0.0, 0.0], outline_um=[20.0, 40.0], pins=_pins(1.0)),
                        dict(inst="u_s1", module="lf_sink", origin_um=[gap, 0.0], outline_um=[20.0, 40.0], pins=_pins(1.0))]
    if split:
        ab["land_pad_tail_split"] = dict(types=["ts"], min_spread_um=400, hop_um=380)
    f = tmp_path / ("plan_split.json" if split else "plan_base.json")
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


def test_rule_and_names():
    cfg = TS.config({"land_pad_tail_split": {"types": ["kv3_pv.*"], "min_spread_um": 400, "hop_um": 380}})
    assert TS.config({}) is None and TS.selected(cfg, "kv3_pv_v12") and not TS.selected(cfg, "kv3_pc_v1")
    assert TS.spread([(0, 0), (300, 400), (-100, 50)]) == 750
    two = {"a": [(0.0, 0.0)], "b": [(1000.0, 0.0)]}
    assert TS.tail_depth(3, two, cfg) == (2, 1000.0)            # ceil(500 / 380) = 2
    assert TS.tail_depth(1, two, cfg) == (1, 1000.0)            # never deeper than the pad: no trunk
    assert TS.tail_depth(37, {"a": [(0.0, 0.0)], "b": [(2464.0, 0.0)]}, cfg)[0] == 4
    assert TS.tail_depth(3, {"a": [(0.0, 0.0), (1000.0, 0.0)]}, cfg) is None       # one core: nothing to split
    assert TS.tail_depth(3, {"a": [(0.0, 0.0)], "b": [(400.0, 0.0)]}, cfg) is None  # inside the spread limit
    assert TS.tail_depth(0, two, cfg) is None
    with pytest.raises(ValueError):
        TS.config({"land_pad_tail_split": {"types": []}})
    with pytest.raises(ValueError):
        TS.config({"land_pad_tail_split": {"types": ["x"], "hop": 1}})


@needs_yosys
def test_key_absent_identical_and_key_on_splits(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_HCPARAM_ALL", "0")     # the tiny cores have no signed parameter record (unrelated gate)
    base, split = tmp_path / "base", tmp_path / "split"
    assert _bind(_plan(tmp_path, False), base, "elab", "bind", "verify") == 0
    assert _bind(_plan(tmp_path, True), split, "elab", "bind", "verify") == 0
    rtl_b = (base / "rtl" / "bt_ts.sv").read_text()
    rtl_s = (split / "rtl" / "bt_ts.sv").read_text()
    pad_b = re.findall(r"ot_dp_dly #\(\.W\(1\), \.D\((\d+)\)\) u_(pd\w+) \(\.clk\(clk\), \.d\((\S+?)\), \.q\((\w+)\)\);", rtl_b)
    pad_s = re.findall(r"ot_dp_dly(?:_keep)? #\(\.W\(1\), \.D\((\d+)\)\) u_(pd\w+) \(\.clk\(clk\), \.d\((\S+?)\), \.q\((\w+)\)\);", rtl_s)
    # base: one shared 3-stage pad per padded bit, read by both cores
    assert len(pad_b) == 5 and {d for d, *_ in pad_b} == {"3"} and "bind_pad_tail_split.json" not in _files(base)
    for _d, nm, _src, _q in pad_b:
        assert rtl_b.count(f"{nm}[0]") == 2
    # split: per bit a 1-stage trunk + a 2-stage copy per core (K = ceil(500 / 380) = 2), each read by one core
    trunk = [x for x in pad_s if "_t_" in x[1]]
    tails = [x for x in pad_s if "_t_" not in x[1]]
    assert len(trunk) == 5 and {d for d, *_ in trunk} == {"1"} and all(src.endswith("]") and "_q[" in src for _d, _n, src, _q in trunk)
    assert len(tails) == 10 and {d for d, *_ in tails} == {"2"}
    # the copies AND the trunks are (* keep *) modules: opt_merge would fold copies back into one flop, and a deeper trunk of
    # the same bit into the copy of a shallower pad (TRUNK-CHAIN 11-20); base pads are plain
    assert rtl_s.count("ot_dp_dly_keep #(") == 15 and "ot_dp_dly_keep" not in rtl_b
    assert all(f"ot_dp_dly_keep #(.W(1), .D(1)) u_{n} " in rtl_s for _d, n, _s, _q in trunk)
    cells_s = (split / "rtl" / "bind_cells.sv").read_text()
    assert "module ot_dp_dly_keep" in cells_s and "(* keep *) reg [W-1:0] r [0:D-1];" in cells_s
    assert "ot_dp_dly_keep" not in (base / "rtl" / "bind_cells.sv").read_text()
    assert {src for _d, _n, src, _q in tails} == {f"{q}[0]" for _d, _n, _s, q in trunk}
    assert sum("_u_s0_" in n for _d, n, *_ in tails) == 5 and sum("_u_s1_" in n for _d, n, *_ in tails) == 5
    for _d, nm, _src, _q in tails:
        assert rtl_s.count(f"{nm}[0]") == 1 and re.fullmatch(r"pd\d+_\w+_\d+", nm)   # still a pad-stage name (R-REACH-5)
    rec = json.loads((split / "bind_pad_tail_split.json").read_text())["types"]["ts"]
    assert rec["split_pads"] == 5 and rec["copies"] == 10 and rec["extra_flops"] == 10 and rec["tail_depths"] == {"2": 5}
    # pre-GPL anchors: one site row per copy stage, at the centroid of the consumer core's pins, type_relay_sites key form
    assert len(rec["sites"]) == 10 * 2 and all(k.endswith((".q", ".r[0]")) for k in rec["sites"])
    assert all(isinstance(v, list) and len(v) == 2 for v in rec["sites"].values())
    assert rec["not_covered"] == dict(r8_strap=0, registered=0, pad_tree=0, position_bank=0) and rec["shared_readers"] == 0
    # same traced depth per sink: the proof passes on both and every record but the split RTL / record is identical
    vb = json.loads((base / "verify_report.json").read_text())
    vs = json.loads((split / "verify_report.json").read_text())
    assert vb["verdict"] == "PASS" and vs["verdict"] == "PASS"
    fb, fs = _files(base), _files(split)
    for k in ("bind_sinks.json", "bind_latency.json", "bus_groups.json"):
        assert k in fb and fb[k] == fs[k], k
    sinks = json.loads(fs["bind_sinks.json"])
    assert {sinks[f"snk.u_s{n}.d0[{i}]"][2] for n in (0, 1) for i in range(8)} == {5}
    changed = {k for k in set(fb) | set(fs) if fb.get(k) != fs.get(k)}
    assert "rtl/bt_ts.sv" in changed and "bind_pad_tail_split.json" in changed
    assert all(not k.startswith("rtl/") or k in ("rtl/bt_ts.sv", "rtl/bind_cells.sv") for k in changed), changed


@needs_yosys
def test_cores_inside_the_spread_keep_the_shared_pad(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_HCPARAM_ALL", "0")
    base, near = tmp_path / "base", tmp_path / "near"
    assert _bind(_plan(tmp_path, False, gap=100.0), base, "elab", "bind") == 0
    assert _bind(_plan(tmp_path, True, gap=100.0), near, "elab", "bind") == 0
    assert (base / "rtl" / "bt_ts.sv").read_bytes() == (near / "rtl" / "bt_ts.sv").read_bytes()
    assert json.loads((near / "bind_pad_tail_split.json").read_text())["types"]["ts"]["split_pads"] == 0


def test_leaf_xy_groups_hard_cores_of_a_soft_leaf():
    """QC st_a: the consumer leaf u_r0 is soft, its SRAM cores are plan rows u_bound.u_u_r0.*; one consumer at their centroid"""
    hc = [dict(inst="u_bound.u_u_r0.u_h9.u_m", origin_um=[0, 0], outline_um=[10, 10]),
          dict(inst="u_bound.u_u_r0.u_hb.u_m", origin_um=[100, 0], outline_um=[10, 10]),
          dict(inst="u_bound.u_u_r1.u_h9.u_m", origin_um=[0, 900], outline_um=[10, 10])]
    t = TS.leaf_table(hc)
    assert TS.leaf_xy(t, "u_r0") == ("u_r0", (55.0, 5.0))
    assert TS.leaf_xy(t, "u_r1") == ("u_r1", (5.0, 905.0))
    assert TS.leaf_xy(t, "u_r2") == (None, None)
    by = {"u_r0": [(55.0, 5.0)], "u_r1": [(5.0, 905.0)]}
    cfg = dict(min_spread_um=400.0, hop_um=380.0)
    assert TS.tail_depth(5, by, cfg) == (2, 950.0)


def test_keep_cell_and_site_rows():
    import bind_pad_tail_split as T
    assert "(* keep *)" in T.KEEP_CELL and "module ot_dp_dly_keep" in T.KEEP_CELL
    assert T.site_rows("u_pd2_x_0_u_r0_5", 2, (1.0004, 2.0)) == {"u_pd2_x_0_u_r0_5.r[0]": [1.0, 2.0], "u_pd2_x_0_u_r0_5.q": [1.0, 2.0]}
    assert T.site_rows("u_p", 1, (3, 4)) == {"u_p.q": [3.0, 4.0]}
    assert T.centroids({"a": [(0, 0), (10, 20)]}) == {"a": (5.0, 10.0)}


# ---- REACH (FABLE-FIX-KV-PV class D 11-19): sub-keys route / require_reach ------------------------------------------------
def test_reach_rule():
    cfg = TS.config({"land_pad_tail_split": {"types": ["t"], "min_spread_um": 400, "hop_um": 300, "route": True,
                                             "require_reach": True}})
    assert cfg["route"] is True and cfg["require_reach"] is True
    off = TS.config({"land_pad_tail_split": {"types": ["t"]}})
    assert off["route"] is False and off["require_reach"] is False
    for bad in ({"route": 1}, {"require_reach": "yes"}):
        with pytest.raises(ValueError):
            TS.config({"land_pad_tail_split": {"types": ["t"], **bad}})
    two = {"a": [(0.0, 0.0)], "b": [(1000.0, 0.0)]}
    assert TS.l1_centre([(0.0, 0.0), (1000.0, 0.0)]) == (500.0, 0.0)
    assert TS.hops(50.0, cfg) == 0 and TS.hops(300.0, cfg) == 1 and TS.hops(301.0, cfg) == 2
    # split pad: trunk src -> T (1,200 um = 4 hops) + tail T -> pin (500 um = 2 hops)
    r = TS.reach(1, two, cfg, src=(-700.0, 0.0))
    assert r == dict(need=6, trunk=4, tail=2, short=5, split=True)
    assert TS.reach(6, two, cfg, src=(-700.0, 0.0))["short"] == 0
    assert TS.reach(1, two, cfg)["need"] == 2                       # unknown source: only the tail is priced
    # shared pad (one core): pad + 1 hops between the in-boundary flop and the pin
    one = {"a": [(2000.0, 0.0), (1990.0, 0.0)]}
    assert TS.reach(0, one, cfg, src=(0.0, 0.0)) == dict(need=6, trunk=6, tail=0, short=6, split=False)
    assert TS.reach(6, one, cfg, src=(0.0, 0.0))["short"] == 0
    # route: a hard core on the straight T -> pin line makes the run a Z through the channel beside it
    wall = [(600.0, -100.0, 800.0, 100.0)]
    assert TS.route_len((500.0, 0.0), (1000.0, 0.0), [])[0] == 500.0
    ln, crossed = TS.route_len((500.0, 0.0), (1000.0, 0.0), wall)
    assert crossed == 0 and ln == 500.0 + 2 * (100.0 + TS.HALO_UM)
    assert TS.tail_need(two, cfg, wall) == 3 and TS.tail_need(two, cfg) == 2
    assert TS.tail_depth(5, two, cfg, wall) == (3, 1000.0) and TS.tail_depth(5, two, cfg) == (2, 1000.0)
    assert TS.tail_depth(5, two, off, wall) == (2, 1000.0)          # "route" off: the boxes are ignored (S / 2 at 380)
    # a pin on its own core edge is not a crossing; a trunk end inside a core is pushed out to its halo
    assert TS.route_len((0.0, 50.0), (500.0, 50.0), [(500.0, 0.0, 700.0, 100.0)]) == (500.0, 0)
    assert TS.push_out((650.0, 10.0), wall) == (600.0 - TS.HALO_UM, 10.0)
    assert TS.core_boxes([dict(origin_um=[10, 20], outline_um=[100, 40], orient="R90")]) == [(10.0, 20.0, 50.0, 120.0)]
    # source point: relay_sites of the in-boundary flop, else the landing band centre
    typ = dict(clock=dict(landing_contract=dict(bands=dict(b_i=dict(rect_um=[0, 0, 20, 10])))),
               relay_sites={"u_bin_c_i.q[0]": [100.0, 50.0], "u_bin_c_i.q[1]": [102.0, 50.0], "u_bin_c_ix.q[0]": [0.0, 0.0]})
    assert TS.src_xy(typ, "b_i") == (10.0, 5.0) and TS.src_xy(typ, "c_i") == (101.0, 50.0) and TS.src_xy(typ, "zz") is None


def _reach_plan(tmp_path, name, far=False, **opt):
    f = _plan(tmp_path, True)
    p = json.loads(f.read_text())
    p["asbuilt"]["land_pad_tail_split"] = dict(types=["ts"], min_spread_um=400, hop_um=380, **opt)
    if far:   # the in-boundary flops of both in buses sited at the far end of the type: a 4-hop trunk the pad 3 cannot hold
        ts = p["partition_types"]["ts"]
        ts["relay_sites"] = {f"u_bin_{b['name']}.q[{j}]": [1990.0, 90.0] for b in ts["buses"] if b["dir"] == "in"
                             for j in range(b["width"])}
    g = tmp_path / name
    g.write_text(json.dumps(p))
    return g


@needs_yosys
def test_reach_record_and_fail_closed(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_HCPARAM_ALL", "0")
    plain, rec, bad = tmp_path / "plain", tmp_path / "rec", tmp_path / "bad"
    assert _bind(_plan(tmp_path, True), plain, "elab", "bind", "verify") == 0
    assert _bind(_reach_plan(tmp_path, "plan_rec.json", route=True), rec, "elab", "bind", "verify") == 0
    # no hard core in the way: same RTL as the plain split, plus the reach record
    assert (rec / "rtl" / "bt_ts.sv").read_bytes() == (plain / "rtl" / "bt_ts.sv").read_bytes()
    assert "reach" not in json.loads((plain / "bind_pad_tail_split.json").read_text())["types"]["ts"]
    rr = json.loads((rec / "bind_pad_tail_split.json").read_text())["types"]["ts"]["reach"]
    assert rr["hop_um"] == 380 and rr["route"] is True
    # every bit feeds both cores 1,000 um apart: tail 2 (no source point: trunk not priced).  The 5 padded bits (pad 3) have
    # the stages; the bits of d1_i both cores read with NO landing pad are short by those 2 stages
    assert max(e["need"] for e in rr["buses"].values()) == 2
    assert rr["buses"]["d1_i"]["min_pad"] == 0 and rr["buses"]["d1_i"]["short"] == 2 and rr["buses"]["d1_i"]["short_pads"] > 0
    # the in-boundary flops planned ~1,560 um from the trunk end: trunk 5 + tail 2
    assert _bind(_reach_plan(tmp_path, "plan_far.json", far=True, route=True), rec, "elab", "bind") == 0
    rr = json.loads((rec / "bind_pad_tail_split.json").read_text())["types"]["ts"]["reach"]["buses"]
    assert max(e["need"] for e in rr.values()) == 7 and max(e["short"] for e in rr.values()) == 7
    # require_reach: a short pad is a bind error (EMIT error: no bound RTL for the type, verify fails)
    try:
        rc = _bind(_reach_plan(tmp_path, "plan_bad.json", require_reach=True), bad, "elab", "bind", "verify")
    except Exception as exc:          # BindError raised through main
        rc = 1
        assert "shorter than the reach" in str(exc)
    assert rc != 0


# ---- BIN-COPY (FABLE-FIX-QC-N N4.1): land_pad_tail_split.wire_leaves -------------------------------------------------
SPW = """`timescale 1ns/1ps
module wlf (input wire ck, input wire [7:0] a, output wire [3:0] c, output wire [3:0] r);
    assign c = {a[7:6], a[1:0]};   // pure wiring (QC st_a qfd_dv_s8_frs form)
    assign r = a[5:2];
endmodule
module lf_c (input wire clk, input wire [3:0] c, input wire [3:0] r, output reg [7:0] q);
    always @(posedge clk) q <= {c, r};
endmodule
module spw (input wire ck, input wire flt, input wire [7:0] a, input wire [7:0] b, output wire [8:0] q0,
            output wire [7:0] q1, output wire [7:0] q2);
    wire [3:0] c; wire [3:0] r;
    wlf u_w (.ck(ck), .a(a), .c(c), .r(r));
    lf_sink u_s0 (.clk(ck), .flt(flt), .d0(a), .d1(b), .q(q0));
    lf_c u_c0 (.clk(ck), .c(c), .r(r), .q(q1));
    lf_c u_c1 (.clk(ck), .c(c), .r(r), .q(q2));
endmodule
"""


def _plan_bin(tmp_path, wire_leaves, name, gap=1000.0, wlf=None):
    src = tmp_path / ("src_" + name)
    shutil.copytree(EX, src)
    die = (src / "die.v").read_text()
    die = die.replace("wire [8:0] sq;", "wire [8:0] sq; wire [7:0] sq1; wire [7:0] sq2;")
    die = die.replace("lf_sink snk (.clk(ck), .flt(fo), .d0(y0), .d1(y1), .q(sq));",
                      "spw snk (.ck(ck), .flt(fo), .a(y0), .b(y1), .q0(sq), .q1(sq1), .q2(sq2));")
    assert "spw snk" in die
    (src / "die.v").write_text(die)
    (src / "spw.sv").write_text(SPW if wlf is None else SPW.replace("assign r = a[5:2];", wlf))
    p = json.loads((EX / "die_plan_lanes.json").read_text())
    ab = p["asbuilt"]
    ab["base"] = str(src)
    ab["files"] = ab["files"] + ["spw.sv"]
    ab["dissolve"] = ab["dissolve"] + ["spw"]
    ts = p["partition_types"]["ts"]
    for b in ts["buses"]:
        b["leaf"] = b["leaf"].replace("core.", "u_s0.")
    ts["outline_um"] = [2000.0, 100.0]
    cpins = [dict(name=f"c[{i}]", layer="M4", xy=[1.0 + i, 10.0]) for i in range(4)]
    ts["hard_cores"] = [dict(inst="u_c0", module="lf_c", origin_um=[0.0, 0.0], outline_um=[20.0, 40.0], pins=cpins),
                        dict(inst="u_c1", module="lf_c", origin_um=[gap, 0.0], outline_um=[20.0, 40.0], pins=cpins)]
    ab["land_pad_tail_split"] = dict(types=["ts"], min_spread_um=400, hop_um=380)
    if wire_leaves:
        ab["land_pad_tail_split"]["wire_leaves"] = wire_leaves
    f = tmp_path / f"plan_{name}.json"
    f.write_text(json.dumps(p))
    return f


def test_bin_copy_config_and_rule():
    cfg = TS.config({"land_pad_tail_split": {"types": ["t"], "wire_leaves": ["wlf"]}})
    assert cfg["wire_leaves"] == frozenset({"wlf"})
    assert TS.config({"land_pad_tail_split": {"types": ["t"]}})["wire_leaves"] == frozenset()
    for bad in ([], "wlf", [1], [""]):
        with pytest.raises(ValueError):
            TS.config({"land_pad_tail_split": {"types": ["t"], "wire_leaves": bad}})
    two = {"a": [(0.0, 0.0)], "b": [(1000.0, 0.0)]}
    assert TS.bin_spread(two, cfg) == 1000.0
    assert TS.bin_spread({"a": [(0.0, 0.0), (1000.0, 0.0)]}, cfg) is None          # one core
    assert TS.bin_spread({"a": [(0.0, 0.0)], "b": [(400.0, 0.0)]}, cfg) is None      # inside the spread limit


@needs_yosys
def test_bin_copy_per_core_and_verify(tmp_path, monkeypatch):
    """u_bin_d0_i q[0,1,6,7] reach u_c0 / u_c1 (1,000 um apart) through the pure-wiring leaf u_w: one kept copy of the
    in-boundary flop per core, 0 added cycles; key without wire_leaves = byte-identical bind; verify proves the wiring"""
    monkeypatch.setenv("OT_HCPARAM_ALL", "0")
    base, on = tmp_path / "base", tmp_path / "on"
    assert _bind(_plan_bin(tmp_path, None, "base"), base, "elab", "bind", "verify") == 0
    assert _bind(_plan_bin(tmp_path, ["wlf"], "on"), on, "elab", "bind", "verify") == 0
    rtl_b = (base / "rtl" / "bt_ts.sv").read_text()
    rtl_o = (on / "rtl" / "bt_ts.sv").read_text()
    assert "ot_dp_dly_keep" not in rtl_b and "bind_bin_copies.json" not in _files(base)
    cp = re.findall(r"ot_dp_dly_keep #\(\.W\(1\), \.D\(1\)\) u_(pd1_\w+) \(\.clk\(clk\), \.d\((\S+?)\), \.q\((\w+)\)\);  "
                    r"// landing pad tail copy for core (\w+):", rtl_o)
    assert sorted((nm, src, tag) for nm, src, _q, tag in cp) == sorted(
        (f"pd1_d0_i_{j}_{c}_0", f"d0_i[{j}]", c) for j in (0, 1, 6, 7) for c in ("u_c0", "u_c1"))
    for nm, _src, _q, _tag in cp:
        assert rtl_o.count(f"{nm}[0]") == 1                           # read by its own core pin only
    # the cores read their copies, never the leaf output; the leaf itself and its other readers are unchanged
    for c in ("u_c0", "u_c1"):
        m = re.search(r"\.c\(([^)]*)\)", rtl_o[rtl_o.index(f"u_{c} ("):])
        assert m and all(f"pd1_d0_i_{j}_{c}_0[0]" in m.group(1) for j in (0, 1, 6, 7)) and "w_u_w" not in m.group(1)
    assert re.search(r"\.r\(w_u_w_r", rtl_o[rtl_o.index("u_u_c0 ("):]) and "wlf u_u_w (" in rtl_o
    # the gen_phys tail-copy siting hook lists them (same marking as the pad tail copies)
    import gen_phys
    rows = gen_phys.tail_copy_rows(on / "rtl")
    assert len(rows) == 8 and {k for _c, k, _g, _t in rows} == {1} and {t for *_x, t in rows} == {"u_c0", "u_c1"}
    assert len({g for _c, _k, g, _t in rows}) == 4                   # one group per in-boundary flop bit
    rec = json.loads((on / "bind_pad_tail_split.json").read_text())["types"]["ts"]
    assert rec["bin_copies"] == dict(bits=4, copies=8, sinks=8, max_spread_um=1000.0) and rec["split_pads"] == 0
    assert len(rec["sites"]) == 8 and rec["sites"]["u_pd1_d0_i_0_u_c1_0.q"] == [1001.0, 10.0] and rec["sites"]["u_pd1_d0_i_6_u_c0_0.q"] == [3.0, 10.0]
    bc = json.loads((on / "bind_bin_copies.json").read_text())["sinks"]
    assert len(bc) == 8 and bc["snk.u_c1.c[2]"] == dict(through="snk.u_w.c[2]", leaf_in="snk.u_w.a[6]", module="wlf")
    vb = json.loads((base / "verify_report.json").read_text())
    vo = json.loads((on / "verify_report.json").read_text())
    assert vb["verdict"] == "PASS" and vo["verdict"] == "PASS" and vo["counts"]["bin_copy"] == 8
    assert "bin_copy" not in vb["counts"] and vo["counts"]["mismatched"] == 0
    fb, fo = _files(base), _files(on)
    for k in ("bind_sinks.json", "bind_latency.json", "bus_groups.json"):
        assert fb[k] == fo[k], k                                      # 0 added cycles: every record unchanged
    changed = {k for k in set(fb) | set(fo) if fb.get(k) != fo.get(k)}
    assert all(not k.startswith("rtl/") or k in ("rtl/bt_ts.sv", "rtl/bind_cells.sv") for k in changed), changed
    # the proof does not trust the record: a record naming another leaf input bit is a BIN_COPY error + mismatch
    bad = json.loads((on / "bind_bin_copies.json").read_text())
    bad["sinks"]["snk.u_c1.c[2]"]["leaf_in"] = "snk.u_w.a[5]"
    (on / "bind_bin_copies.json").write_text(json.dumps(bad))
    assert _bind(_plan_bin(tmp_path, ["wlf"], "on2"), on, "verify") != 0
    vr = json.loads((on / "verify_report.json").read_text())
    assert vr["verdict"] == "FAIL" and any("BIN_COPY snk.u_c1.c[2]" in e for e in vr["graph_errors"])
    # without the record the re-pointed sinks are plain as-built mismatches
    (on / "bind_bin_copies.json").unlink()
    assert _bind(_plan_bin(tmp_path, ["wlf"], "on3"), on, "verify") != 0
    assert json.loads((on / "verify_report.json").read_text())["counts"]["mismatched"] == 8


@needs_yosys
def test_bin_copy_near_cores_and_impure_leaf(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("OT_HCPARAM_ALL", "0")
    base, near, imp = tmp_path / "base", tmp_path / "near", tmp_path / "imp"
    assert _bind(_plan_bin(tmp_path, None, "base", gap=100.0), base, "elab", "bind") == 0
    assert _bind(_plan_bin(tmp_path, ["wlf"], "near", gap=100.0), near, "elab", "bind") == 0
    assert (base / "rtl" / "bt_ts.sv").read_bytes() == (near / "rtl" / "bt_ts.sv").read_bytes()
    assert not (near / "bind_bin_copies.json").exists()
    assert json.loads((near / "bind_pad_tail_split.json").read_text())["types"]["ts"]["bin_copies"]["copies"] == 0
    # a declared wire leaf that holds logic is refused (fail closed), never bypassed
    rc = _bind(_plan_bin(tmp_path, ["wlf"], "imp", wlf="assign r = ~a[5:2];"), imp, "elab", "bind")
    txt = capsys.readouterr()
    rep = imp / "bind_report.json"
    errs = json.loads(rep.read_text()).get("errors") if rep.is_file() else []
    assert rc != 0 or errs
    assert "wire_leaves" in txt.out + txt.err + json.dumps(errs) and "not a plain input port reference" in txt.out + txt.err + json.dumps(errs)


# ---- KV-D23-REACH 11-18: pipe tail split (sub-key "pipes") ------------------------------------------------------------------
SPAR_PIPE = """`timescale 1ns/1ps
module mrly (input wire ck, input wire [7:0] a, output reg [7:0] b);
    always @(posedge ck) b <= a;
endmodule
module spar (input wire ck, input wire flt, input wire [7:0] a, input wire [7:0] b, output wire [8:0] q0,
             output wire [8:0] q1);
    wire [7:0] m; wire [7:0] m1; wire [7:0] m2; wire [7:0] m3; wire mf;
    lf_b_nid u_m (.clk(ck), .i(b), .o(m), .flt(mf));
    mrly u_r0 (.ck(ck), .a(m), .b(m1));
    mrly u_r1 (.ck(ck), .a(m1), .b(m2));
    mrly u_r2 (.ck(ck), .a(m2), .b(m3));
    lf_sink u_s0 (.clk(ck), .flt(flt), .d0(a), .d1(m3), .q(q0));
    lf_sink u_s1 (.clk(ck), .flt(flt), .d0(a), .d1(m3), .q(q1));
endmodule
"""


def _plan_pipe(tmp_path, opt, gap=1000.0, tag="p"):
    """the sink partition holds a source leaf u_m whose output reaches d1 of BOTH cores through 3 as-built relay stages:
    bind keeps them as ONE intra-partition pipe ot_dp_dly #(.W(8), .D(3)) u_d3_u_m_o read by 16 pins on two cores"""
    src = tmp_path / "srcp"
    if not src.exists():
        shutil.copytree(EX, src)
        die = (src / "die.v").read_text()
        die = die.replace("wire [8:0] sq;", "wire [8:0] sq; wire [8:0] sq1;")
        die = die.replace("lf_sink snk (.clk(ck), .flt(fo), .d0(y0), .d1(y1), .q(sq));",
                          "spar snk (.ck(ck), .flt(fo), .a(y0), .b(y1), .q0(sq), .q1(sq1));")
        assert "spar snk" in die
        (src / "die.v").write_text(die)
        (src / "spar.sv").write_text(SPAR_PIPE)
    p = json.loads((EX / "die_plan_lanes.json").read_text())
    ab = p["asbuilt"]
    ab["base"] = str(src)
    ab["files"] = ab["files"] + ["spar.sv"]
    ab["dissolve"] = ab["dissolve"] + ["spar"]
    ab["transport"] = ab["transport"] + [{"module": "mrly", "map": {"b": "a"}, "drop_in": ["ck"], "stages": 1}]
    ts = p["partition_types"]["ts"]
    for b in ts["buses"]:
        b["leaf"] = "u_m.i" if b["name"] == "d1_i" else b["leaf"].replace("core.d0", "u_s0.d0").replace("core.", "u_s0.")
    ts["outline_um"] = [2000.0, 100.0]
    ts["hard_cores"] = [dict(inst="u_s0", module="lf_sink", origin_um=[0.0, 0.0], outline_um=[20.0, 40.0], pins=_pins(1.0)),
                        dict(inst="u_s1", module="lf_sink", origin_um=[gap, 0.0], outline_um=[20.0, 40.0], pins=_pins(1.0))]
    if opt is not None:
        ab["land_pad_tail_split"] = dict(types=["ts"], min_spread_um=400, hop_um=380, **opt)
    f = tmp_path / f"plan_{tag}.json"
    f.write_text(json.dumps(p))
    return f


def test_pipe_rule():
    cfg = TS.config({"land_pad_tail_split": {"types": ["kv3_pv.*"], "pipes": True}})
    assert cfg["pipes"] is True and TS.config({"land_pad_tail_split": {"types": ["x"]}})["pipes"] is False
    assert TS.pipe_depth(60, [2804.3, 900.0], cfg) == 4          # ceil(1402 / 380), one K per pipe = the widest split bit
    assert TS.pipe_depth(3, [1000.0], cfg) == 2
    assert TS.pipe_depth(2, [2804.3], cfg) == 1                  # one trunk stage always stays: K <= N - 1
    assert TS.pipe_depth(1, [2804.3], cfg) == 0 and TS.pipe_depth(9, [], cfg) == 0
    with pytest.raises(ValueError):
        TS.config({"land_pad_tail_split": {"types": ["x"], "pipes": 1}})


@needs_yosys
def test_pipes_key_absent_identical_and_key_on_splits_the_pipe(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_HCPARAM_ALL", "0")
    base, pads, split = tmp_path / "base", tmp_path / "pads", tmp_path / "split"
    assert _bind(_plan_pipe(tmp_path, None, tag="b"), base, "elab", "bind", "verify") == 0
    assert _bind(_plan_pipe(tmp_path, {}, tag="k"), pads, "elab", "bind") == 0
    assert _bind(_plan_pipe(tmp_path, {"pipes": True}, tag="s"), split, "elab", "bind", "verify") == 0
    rtl_b = (base / "rtl" / "bt_ts.sv").read_text()
    rtl_s = (split / "rtl" / "bt_ts.sv").read_text()
    # base: ONE 8-bit 3-stage pipe from the source leaf, read by d1 of both cores (16 pins)
    assert re.findall(r"ot_dp_dly #\(\.W\((\d+)\), \.D\((\d+)\)\) u_(d\d+_\w+) ", rtl_b) == [("8", "3", "d3_u_m_o")]
    assert rtl_b.count(".d1(d3_u_m_o[7:0])") == 2
    # the pad key without "pipes" changes nothing in the RTL (pipes are opt-in) and writes no pipe record
    assert (pads / "rtl" / "bt_ts.sv").read_text() == rtl_b
    assert "pipes_split" not in json.loads((pads / "bind_pad_tail_split.json").read_text())["types"]["ts"]
    # pipes on: trunk D = 3 - 2, no shared tail (every reader is split), 8 bits x 2 cores kept 2-stage copies
    assert re.findall(r"ot_dp_dly #\(\.W\((\d+)\), \.D\((\d+)\)\) u_(d\d+_\w+) ", rtl_s) == [("8", "1", "d3_u_m_o_t")]
    cp = re.findall(r"ot_dp_dly_keep #\(\.W\(1\), \.D\((\d+)\)\) u_(pd\w+) \(\.clk\(clk\), \.d\((\S+?)\), \.q\((\w+)\)\);"
                    r"  // landing pad tail copy for core (\w+):", rtl_s)
    assert len(cp) == 16 and {c[0] for c in cp} == {"2"}
    assert sorted(c[2] for c in cp) == sorted(f"d3_u_m_o_t[{i}]" for i in range(8) for _ in range(2))
    assert sum(c[4] == "u_s0" for c in cp) == 8 and sum(c[4] == "u_s1" for c in cp) == 8
    for _d, nm, _src, q, core in cp:
        assert nm == q and re.fullmatch(r"pd2_d3_u_m_o_\d_" + core + "_3", nm) and rtl_s.count(f"{nm}[0]") == 1
    assert not re.search(r"\bd3_u_m_o\[", rtl_s)                    # no pin reads the shared wire any more
    for n in (0, 1):                                                  # each core reads its own copies, in bit order
        blk = re.search(r"lf_sink u_u_s%d \((.*?)\n    \);" % n, rtl_s, re.S).group(1)
        assert re.search(r"\.d1\(\{" + ", ".join(f"pd2_d3_u_m_o_{i}_u_s{n}_3\\[0\\]" for i in range(7, -1, -1)) + r"\}\)", blk), blk
    rec = json.loads((split / "bind_pad_tail_split.json").read_text())["types"]["ts"]["pipes_split"]
    assert rec["pipes"] == 1 and rec["split_pipes"] == 1 and rec["split_bits"] == 8 and rec["copies"] == 16
    assert rec["extra_flops"] == 16 and rec["tail_depths"] == {"2": 1} and rec["shared_tail_pipes"] == 0
    assert rec["max_spread_um"] == 1000.0 and rec["not_covered"] == dict(depth1=0, inner_strap=0, port_pipe=0, registered=0)
    assert len(rec["sites"]) == 16 * 2
    # same traced depth per sink: the proof passes on both; sink / latency records are identical
    assert json.loads((base / "verify_report.json").read_text())["verdict"] == "PASS"
    assert json.loads((split / "verify_report.json").read_text())["verdict"] == "PASS"
    fb, fs = _files(base), _files(split)
    for k in ("bind_sinks.json", "bind_latency.json", "bus_groups.json"):
        assert k in fb and fb[k] == fs[k], k
    changed = {k for k in set(fb) | set(fs) if fb.get(k) != fs.get(k)}
    assert all(not k.startswith("rtl/") or k in ("rtl/bt_ts.sv", "rtl/bind_cells.sv") for k in changed), changed
    # the siting hook lists the pipe copies with the pad-copy rule (same line form, u_pd<K>_ names), grouped per trunk bit
    import gen_phys
    rows = gen_phys.tail_copy_rows(split / "rtl")
    assert len(rows) == 16 and {r[1] for r in rows} == {2} and len({r[2] for r in rows}) == 8


@needs_yosys
def test_pipe_cores_inside_the_spread_are_not_split(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_HCPARAM_ALL", "0")
    base, near = tmp_path / "base", tmp_path / "near"
    assert _bind(_plan_pipe(tmp_path, None, gap=100.0, tag="b"), base, "elab", "bind") == 0
    assert _bind(_plan_pipe(tmp_path, {"pipes": True}, gap=100.0, tag="n"), near, "elab", "bind") == 0
    assert (base / "rtl" / "bt_ts.sv").read_bytes() == (near / "rtl" / "bt_ts.sv").read_bytes()
    assert json.loads((near / "bind_pad_tail_split.json").read_text())["types"]["ts"]["pipes_split"]["split_pipes"] == 0


# ---- R8-KEEP (FABLE-FIX-QC-STRAP 11-21): land_pad_tail_split.r8_keep ---------------------------------------------------
def test_r8_keep_config_and_rule():
    assert TS.config({"land_pad_tail_split": {"types": ["t"]}})["r8_keep"] is False
    assert TS.config({"land_pad_tail_split": {"types": ["t"], "r8_keep": True}})["r8_keep"] is True
    with pytest.raises(ValueError):
        TS.config({"land_pad_tail_split": {"types": ["t"], "r8_keep": 1}})
    ln = ("    ot_dp_dly #(.W({w}), .D({d})) u_r8b_strap_r8pad_u_r{k}_{p}_f (.clk(clk), .d({src}), "
          ".q(r8b_strap_r8pad_u_r{k}_{p}_f));  // R8 strap site strap_r8pad_u_r{k}_{p}: fixed common pad {d}")
    cnt = ("    ot_dp_dly_cnt #(.W(4), .DMAX(1)) u_r8b_strap_r8pad_u_r0_rs_n_c_p (.clk(clk), .strap_cnt(strap_r8pad_u_r0_rs_n_c_p), "
           ".d(r8b_strap_r8pad_u_r0_rs_n_c_p_f), .q(r8b_strap_r8pad_u_r0_rs_n_c_p));  // R8 strap-count bank (pad = 5 + s)")
    body = [ln.format(w=4, d=5, k=k, p="rs_n_c_p", src="x_hc1_i_q[3:0]") for k in range(4)]
    body += [ln.format(w=64, d=5, k=k, p="rs_n_hi_p", src=f"x_hc1_i_q[{131 + 128 * k}:{68 + 128 * k}]") for k in range(4)]
    body += [ln.format(w=4, d=6, k=9, p="rs_n_c_p", src="x_hc1_i_q[3:0]"), cnt,
             "    ot_dp_dly #(.W(4), .D(5)) u_d5_x (.clk(clk), .d(x_hc1_i_q[3:0]), .q(d5_x));",
             ln.format(w=2, d=3, k=0, p="a", src="{x_q[1], y_q[0]}").replace("// R8 strap", "// INNER strap"),
             ln.format(w=2, d=3, k=1, p="a", src="{x_q[1], y_q[0]}").replace("// R8 strap", "// INNER strap")]
    base = list(body)
    rec = TS.r8_keep(body)
    assert [(r["width"], r["depth"], len(r["insts"]), r["extra_flops"]) for r in rec] == [(2, 3, 2, 6), (4, 5, 4, 60)]
    assert rec[1]["insts"] == [f"u_r8b_strap_r8pad_u_r{k}_rs_n_c_p_f" for k in range(4)] and rec[1]["d"] == "x_hc1_i_q[3:0]"
    changed = [i for i, (a, b) in enumerate(zip(base, body)) if a != b]
    assert changed == [0, 1, 2, 3, 11, 12]                  # only the two shared groups; hi buses, depth 6, bank, u_d5 untouched
    for i in changed:
        assert body[i] == base[i].replace("    ot_dp_dly #(", "    ot_dp_dly_keep #(", 1)
    assert TS.r8_keep(list(base[4:9])) == []                # no shared group: nothing changes


def test_require_pin_tables_fails_closed_when_no_pins_resolve(tmp_path):
    """PINS-GUARD: declared pins_file, nothing resolves beside the plan -> ValueError; env override; partial / present ok."""
    hcs = [dict(inst="u_a", pins_file="pins/a.json"), dict(inst="u_b", pins_file="pins/b.json")]
    with pytest.raises(ValueError, match="none resolves"):
        TS.require_pin_tables(hcs, tmp_path, "t0", environ={})
    assert TS.require_pin_tables(hcs, tmp_path, "t0", environ={TS.NO_PINS_ENV: "1"}) == ["pins/a.json", "pins/b.json"]
    (tmp_path / "pins").mkdir()
    (tmp_path / "pins" / "a.json").write_text("[]")
    assert TS.require_pin_tables(hcs, tmp_path, "t0", environ={}) == ["pins/b.json"]
    assert TS.require_pin_tables([dict(inst="u_c")], tmp_path / "nowhere", "t0", environ={}) == []
    assert TS.require_pin_tables([dict(inst="u_d", pins=[{"name": "x"}], pins_file="pins/zz.json")], tmp_path / "nowhere",
                                 "t0", environ={}) == []
