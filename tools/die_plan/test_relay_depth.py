"""S81-COLGEN-3 11-17: relay_depth (S81-TYPES-R3 col relay class) -- extra relay-named stages after a named source leaf output,
declared per sink bit; relay_mid fail switch; relay_depth.py rows."""
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind
import gen_phys
import schema
from test_bind_wavefront import emitter, plan


def vehicle(rows):
    raw = plan()
    raw["partition_types"]["src"]["relay_depth"] = rows
    b = emitter(raw)
    part = next(p for p in b.parts if b.parts[p]["type"] == "src")
    b.F.cells = [SimpleNamespace(path="x.u_y_rt_1", ports={"o": [1, 2, 3], "ck": [9]}, module="dsfd_rly_3_WE", params={}),
                 SimpleNamespace(path="x.u_sink", ports={"i": [1, 2, 3], "ck": [9]}, module="core_sink", params={})]
    b.G.dirs = {0: {"o": "output", "ck": "input"}, 1: {"i": "input", "ck": "input"}}
    b.G.kind = ["leaf", "leaf"]
    b.members[part] = [0, 1]
    b.sinks = {(1, "i", k): ("int", 0, "o", k, 0) for k in range(3)}
    b.sinks[(1, "ck", 0)] = ("clk", "core")
    b.sinks[(0, "ck", 0)] = ("clk", "core")
    b.rel_of = lambda ci: ("u_y_rt_1", "u_sink")[ci]
    return b, part


def test_rows_absent_is_off():
    assert bind.relay_depth_map({}, "t") == {}
    assert bind.relay_depth_map({"partition_types": {"t": {}}}, "t") == {}


def test_map_and_duplicate_rows():
    p = {"partition_types": {"t": {"relay_depth": [{"inst": "u_y_rt_20a_3", "D": 2}, {"inst": "u_y_x2_0", "port": "q", "D": 1}]}}}
    assert bind.relay_depth_map(p, "t") == {("u_y_rt_20a_3", "o"): 2, ("u_y_x2_0", "q"): 1}
    p["partition_types"]["t"]["relay_depth"].append({"inst": "u_y_x2_0", "port": "q", "D": 3})
    with pytest.raises(bind.BindError, match="listed twice"):
        bind.relay_depth_map(p, "t")


def test_emit_adds_named_single_stages_and_declares_cycles():
    b, part = vehicle([{"inst": "u_y_rt_1", "D": 3, "path_um": 1200.0}])
    text, _ = b.emit_type("src", part)
    stages = re.findall(r"ot_dp_dly #\(\.W\(3\), \.D\(1\)\) (u_y_xd_\w+) \(", text)
    assert len(stages) == 3 and len(set(stages)) == 3                       # D separate relay groups, 1 cycle each
    assert all(re.search(r"[._]u_y_", "." + s) for s in stages)             # matches relay_mid RELAY_MID_RE after flattening
    assert "u_pc_lp_" not in text                                           # lp_even.tcl (straight line) must not claim them
    assert re.search(r"\.i\(lp_\w+\[2:0\]\)", text)                       # the sink reads the last stage
    rec = getattr(b, "core_input_pipe")
    assert sorted(rec.values()) == [3, 3, 3] and all(k.endswith(("[0]", "[1]", "[2]")) for k in rec)


def test_emit_unchanged_without_rows():
    b, part = vehicle([])
    text, _ = b.emit_type("src", part)
    assert "u_y_xd_" not in text and not getattr(b, "core_input_pipe", {})


def test_schema_validates_rows():
    import jsonschema
    node = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["relay_depth"]
    jsonschema.validate([{"inst": "u_y_a_0", "D": 2, "path_um": 700.5, "stages_existing": 1}], node)
    for bad in ([{"inst": "u_y_a_0", "D": 17}], [{"inst": "u_y_a_0"}], [{"D": 1}], [{"inst": "x", "D": 1, "zz": 1}]):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, node)


def test_relay_hop_fail_switch(monkeypatch):
    assert not gen_phys._relay_hop_fail({}, "col_h9_r0_p2__t1__x")
    assert gen_phys._relay_hop_fail({"relay_hop_fail": True}, "t")
    assert gen_phys._relay_hop_fail({"relay_hop_fail_types": ["col_h9_r0_p2"]}, "col_h9_r0_p2__t1__x")
    assert not gen_phys._relay_hop_fail({"relay_hop_fail_types": ["col_h9_r0_p2"]}, "col_h9_r0_p3__t1__x")
    monkeypatch.setenv("OT_RELAY_POLY_FAIL", "1")
    assert gen_phys._relay_hop_fail({}, "anything")


def test_relay_mid_tcl_fail_hook_present_and_parses():
    import shutil
    import subprocess
    d = Path(__file__).resolve().parent
    src = (d / "relay_mid.tcl").read_text()
    assert "OT_RELAY_POLY_FAIL" in src and "rm_polybad" in src
    if shutil.which("tclsh"):
        r = subprocess.run(["tclsh"], input=f"set f [open {d / 'relay_mid.tcl'}]; set s [read $f]; if {{![info complete $s]}} {{exit 3}}",
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr


def test_depth_arithmetic_rule():
    """stations needed = ceil(path / 405) - 1, so every one of stations + 1 hops is <= 405"""
    import math
    for path, existing, extra in ((746, 1, 0), (1122, 1, 1), (1340, 1, 2), (405, 0, 0), (406, 0, 1), (670, 1, 0), (1700, 2, 2)):
        need = max(0, math.ceil(path / 405) - 1)
        assert max(0, need - existing) == extra
        assert path / (existing + max(0, need - existing) + 1) <= 405 + 1e-9


def test_latcheck_internal_pipe_gate(tmp_path):
    """relay_depth rows -> bind_core_input_pipe.json ack is a WARNING naming S81-DIE-R3 (r703/r704); no rows = no check"""
    import lane_asbuilt_latency as LAL
    rec = {"x.u_sink.i[0]": 2, "x.u_sink.i[1]": 2}
    (tmp_path / "bind_core_input_pipe.json").write_text(json.dumps(rec))
    off = {"partition_types": {"t": {}}}
    assert LAL.internal_pipe_check(off, tmp_path) == ([], {})
    on = {"partition_types": {"t": {"relay_depth": [{"inst": "u_y_a", "D": 2}]}}}
    errs, info = LAL.internal_pipe_check(on, tmp_path)
    assert len(errs) == 1 and "INTERNAL_PIPE_UNACKED" in errs[0] and "S81-DIE-R3" in errs[0] and "WARN" in errs[0] and info["cycles"] == 4 and info["sink_bits"] == 2
    on["latency"] = {"internal_pipe_ack": {"digest": LAL.internal_pipe_digest(rec)}}
    assert LAL.internal_pipe_check(on, tmp_path)[0] == []
    rec["x.u_sink.i[2]"] = 1                                           # a changed record is no longer acknowledged
    (tmp_path / "bind_core_input_pipe.json").write_text(json.dumps(rec))
    assert LAL.internal_pipe_check(on, tmp_path)[0]
    import jsonschema
    jsonschema.validate(on["latency"], schema.SCHEMA["properties"]["latency"])


def test_sink_side_rows_direct_wire_and_fail_closed():
    b, part = vehicle([{"inst": "u_sink", "port": "i", "side": "sink", "bits": [0, 1], "D": 2}])
    text, _ = b.emit_type("src", part)
    assert len(re.findall(r"ot_dp_dly #\(\.W\(2\), \.D\(1\)\) u_y_xd_u_sink_i_0_\d ", text)) == 2     # bits 0..1 only
    assert re.search(r"\.i\(\{?lp_\w+\[1:0\], ?w_u_y_rt_1_o\[2\]\}?\)|\.i\(\{lp_\w+\[1\], lp_\w+\[0\], w_u_y_rt_1_o\[2\]\}\)", text) \
        or "lp_u_sink_i_0" in text
    assert sorted(b.core_input_pipe) == ["x.u_sink.i[0]", "x.u_sink.i[1]"]
    b2, part2 = vehicle([{"inst": "u_nope", "port": "i", "side": "sink", "D": 1}])
    with pytest.raises(bind.BindError, match="matched no internal sink"):
        b2.emit_type("src", part2)
    b3, part3 = vehicle([{"inst": "u_y_rt_1", "D": 1}, {"inst": "u_sink", "port": "i", "side": "sink", "D": 1}])
    with pytest.raises(bind.BindError, match="also has a source-level pipe"):
        b3.emit_type("src", part3)
    p = {"partition_types": {"t": {"relay_depth": [{"inst": "s", "port": "i", "side": "sink", "bits": [0, 3], "D": 1},
                                                   {"inst": "s", "port": "i", "side": "sink", "bits": [3, 5], "D": 2}]}}}
    with pytest.raises(bind.BindError, match="overlap"):
        bind.relay_depth_sink_map(p, "t")


def _rows_vehicle(monkeypatch, cores, paths, pins, text):
    import core_conns_from_bind as CC
    import relay_depth as RD
    monkeypatch.setattr(CC, "trace", lambda plan_, tn, text_, repo=None: {"paths": paths})
    monkeypatch.setattr(RD, "_pin_table", lambda hc, plan_dir: pins[hc["inst"]])
    raw = {"partition_types": {"t": {"outline_um": [1200.0, 400.0], "hard_cores": [
        dict(inst=i, origin_um=[x, y], outline_um=[w, h], pins=1) for i, (x, y, w, h) in cores.items()]}}}
    return RD.type_rows(raw, "t", text)


def test_rows_use_bound_leaf_name_with_content_prefix(monkeypatch):
    """FABLE-FIX-S81-BANKLEAF 11-18: col r0 p1/p2/p4/p5 keep the content instance in the bound leaf name (u_u_r0_u_t0); a direct
    macro-to-macro wire there is a sink row on u_r0_u_t0, not `unfixed`; the _nx form (u_u_t0) still gives u_t0"""
    cores = {"u_r0.u_cf": (0.0, 0.0, 40.0, 40.0), "u_r0.u_t0": (900.0, 0.0, 40.0, 40.0)}
    pins = {"u_r0.u_cf": {"xa": {"0": (40.0, 20.0)}}, "u_r0.u_t0": {"xai": {"0": (900.0, 20.0)}}}
    paths = [dict(dir="in", core="u_r0.u_t0", port="xai", partner="u_r0.u_cf.xa", bit_ranges=[[0, 0]], stages_existing=0, via=[])]
    for inst, want in (("u_u_r0_u_t0", "u_r0_u_t0"), ("u_u_t0", "u_t0")):
        text = f"module t;\n    cf {inst.replace('t0', 'cf')} (.xa(n));\n    st #(.A(1)) {inst} (.xai(n));\nendmodule\n"
        rows, rep = _rows_vehicle(monkeypatch, cores, paths, pins, text)
        assert rep["unfixed"] == [] and rows == [dict(inst=want, port="xai", side="sink", bits=[0, 0], D=2,
                                                       path_um=rows[0]["path_um"], stages_existing=0)]
        assert rows[0]["path_um"] == 860.0
    rows, rep = _rows_vehicle(monkeypatch, cores, paths, pins, "module t;\n    big u_u_r0 (.x(n));\nendmodule\n")
    assert rows == [] and len(rep["unfixed"]) == 1 and "sub-cores" in rep["unfixed"][0]["reason"]


def test_direct_wire_is_flight_and_read_loops_get_no_row(monkeypatch):
    """a direct wire crosses the cores (flight length): a halo-closed channel needs no station; a cfg ROM read loop never
    gets a row (a stage on one ROM breaks the sequencer's fixed read latency) and is `unfixed` only over the reach"""
    cores = {"u_a": (100.0, 100.0, 400.0, 100.0), "u_b": (100.0, 212.0, 400.0, 100.0),
             "u_s": (60.0, 204.0, 20.0, 4.0), "u_k": (540.0, 204.0, 20.0, 4.0)}
    pins = {"u_s": {"o": {"0": (300.0, 206.0)}, "a": {"0": (80.0, 206.0)}},
            "u_k": {"i": {"0": (480.0, 206.0)}, "addr_in": {"0": (540.0, 206.0)}}, "u_a": {}, "u_b": {}}
    paths = [dict(dir="in", core="u_k", port="i", partner="u_s.o", bit_ranges=[[0, 0]], stages_existing=0, via=[])]
    text = "module t;\n    s u_u_s (.o(n));\n    k u_u_k (.i(n));\nendmodule\n"
    rows, rep = _rows_vehicle(monkeypatch, cores, paths, pins, text)
    assert rows == [] and rep["unfixed"] == []
    assert rep["flight_measured"] == [dict(core="u_k", port="i", partner="u_s.o", path_um=180.0, padded_um=None)]
    import relay_depth as RD
    assert RD._is_read_loop("ot_s81_cfg7_seq", "a", "ot_rom_4096x72_m8", "addr_in")
    assert RD._is_read_loop("ot_s81_cfg7_seq_bfp", "ce6", "ot_rom_4096x72_m8", "ce_in")
    assert RD._is_read_loop("ot_rom_4096x72_m8", "rd_out", "ot_s81_cfg7_seq", "q5")
    assert not RD._is_read_loop("ot_s81_cfg7_seq", "st", "ot_s81_sstn_base566", "c0")
    loop = [dict(dir="in", core="u_k", port="addr_in", partner="u_s.a", bit_ranges=[[0, 0]], stages_existing=0, via=[])]
    for kx, n_unfixed in ((540.0, 1), (300.0, 0)):
        cores2 = dict(cores, u_k=(kx, 204.0, 20.0, 4.0))
        pins2 = dict(pins, u_k={"addr_in": {"0": (kx, 206.0)}})
        monkeypatch.setattr(RD, "_pin_table", lambda hc, plan_dir: pins2[hc["inst"]])
        import core_conns_from_bind as CC
        monkeypatch.setattr(CC, "trace", lambda plan_, tn, text_, repo=None: {"paths": loop})
        raw = {"partition_types": {"t": {"outline_um": [1200.0, 400.0], "hard_cores": [
            dict(inst=i, origin_um=[x, y], outline_um=[w, h], pins=1,
                 module={"u_s": "ot_s81_cfg7_seq", "u_k": "ot_rom_4096x72_m8"}.get(i, "core"))
            for i, (x, y, w, h) in cores2.items()]}}}
        rows, rep = RD.type_rows(raw, "t", text)
        assert rows == [] and len(rep["read_loops"]) == 1 and len(rep["unfixed"]) == n_unfixed


def test_merge_equalise_per_content_module():
    import relay_depth as RD
    raw = {"partition_types": {"a": {"contents": [{"module": "m"}]}, "b": {"contents": [{"module": "m"}], "relay_depth": [{"inst": "old", "D": 1}]},
                               "c": {"contents": [{"module": "n"}], "relay_depth": [{"inst": "stale", "D": 1}]}}}
    rep = [dict(type="a", rows_data=[dict(inst="u_y_r", port="o", D=1, path_um=500.0),
                                     dict(inst="u_t0", port="xai", side="sink", bits=[0, 3], D=1, path_um=420.0)]),
           dict(type="b", rows_data=[dict(inst="u_y_r", port="o", D=2, path_um=900.0)]),
           dict(type="c", rows_data=[])]
    import copy
    p1 = copy.deepcopy(raw)
    assert RD.apply_reports(p1, [rep]) == 3 and len(p1["partition_types"]["b"]["relay_depth"]) == 1
    assert "relay_depth" not in p1["partition_types"]["c"]
    p2 = copy.deepcopy(raw)
    assert RD.apply_reports(p2, [rep], equalise=True) == 4
    a, b = p2["partition_types"]["a"]["relay_depth"], p2["partition_types"]["b"]["relay_depth"]
    assert a == b and [(x["inst"], x["D"]) for x in a] == [("u_y_r", 2), ("u_t0", 1)]
    rep[1]["rows_data"].append(dict(inst="u_t0", port="xai", side="sink", bits=[2, 5], D=1, path_um=1.0))
    with pytest.raises(ValueError, match="bit runs"):
        RD.apply_reports(copy.deepcopy(raw), [rep], equalise=True)


def test_lane_fifo_outputs_stay_aligned(monkeypatch):
    """cf.cc -> t0.cci is over the reach, cf.xa -> t0.xai is not: both get the stage (payload and control on one edge)"""
    cores = {"u_cf": (0.0, 0.0, 40.0, 40.0), "u_t0": (500.0, 0.0, 40.0, 40.0)}
    pins = {"u_cf": {"cc": {"0": (0.0, 20.0)}, "xa": {"0": (40.0, 20.0), "1": (40.0, 22.0)}, "st": {"0": (40.0, 30.0)}},
            "u_t0": {"cci": {"0": (540.0, 20.0)}, "xai": {"0": (430.0, 20.0), "1": (430.0, 22.0)}, "so": {"0": (430.0, 30.0)}}}
    paths = [dict(dir="in", core="u_t0", port="cci", partner="u_cf.cc", bit_ranges=[[0, 0]], stages_existing=0, via=[]),
             dict(dir="in", core="u_t0", port="xai", partner="u_cf.xa", bit_ranges=[[0, 1]], stages_existing=0, via=[]),
             dict(dir="in", core="u_cf", port="st", partner="u_t0.so", bit_ranges=[[0, 0]], stages_existing=0, via=[])]
    text = "module t;\n    cf u_u_cf (.cc(n));\n    st u_u_t0 (.cci(n));\nendmodule\n"
    import core_conns_from_bind as CC
    import relay_depth as RD
    monkeypatch.setattr(CC, "trace", lambda plan_, tn, text_, repo=None: {"paths": paths})
    monkeypatch.setattr(RD, "_pin_table", lambda hc, plan_dir: pins[hc["inst"]])
    raw = {"partition_types": {"t": {"outline_um": [1200.0, 400.0], "hard_cores": [
        dict(inst=i, origin_um=[x, y], outline_um=[w, h], pins=1, module={"u_cf": "dsfd_cfifo_crs4"}.get(i, "ot_s81_sstn_base566"))
        for i, (x, y, w, h) in cores.items()]}}}
    rows, rep = RD.type_rows(raw, "t", text)
    assert [(r["inst"], r["port"], r["bits"], r["D"]) for r in rows] == [("u_t0", "cci", [0, 0], 1), ("u_t0", "xai", [0, 1], 1)]
    assert len(rep["aligned_groups"]) == 2 and rep["unfixed"] == []


def test_rows_match_dotted_leaf_names():
    """FABLE-FIX-S81-BANKLEAF 11-18: a leaf under a content instance has the rel u_r0.u_sink and the instance name
    u_u_r0_u_sink; relay_depth.py rows carry the instance-name form (u_r0_u_sink) and must match it"""
    b, part = vehicle([{"inst": "u_r0_u_sink", "port": "i", "side": "sink", "bits": [0, 1], "D": 1},
                       ])
    b.rel_of = lambda ci: ("u_r0.u_y_rt_1", "u_r0.u_sink")[ci]
    text, _ = b.emit_type("src", part)
    assert len(re.findall(r"ot_dp_dly #\(\.W\(2\), \.D\(1\)\) u_y_xd_u_r0_u_sink_i_0_0 ", text)) == 1
    b2, part2 = vehicle([{"inst": "u_r0_u_y_rt_1", "D": 1}])
    b2.rel_of = lambda ci: ("u_r0.u_y_rt_1", "u_r0.u_sink")[ci]
    text2, _ = b2.emit_type("src", part2)
    assert "u_y_xd_" in text2


def test_slice_c_bundles_stay_aligned_and_norm_gate_gets_no_row(monkeypatch):
    """FABLE-FIX-S81-SLICEC 11-20: egg.g_v / g_c (800 um, D 1) and egg.g (824 um, D 2) are one valid / data bundle into xr:
    all three get D 2.  xr.cfg_v / cfg_d into cap are another group of the same source module.  egn.o_r -> egg.n_rh is the
    fixed-latency norm -> gate wire: never a row, `unfixed` (core placement) over the reach."""
    cores = {"u_xr": (0.0, 0.0, 40.0, 40.0), "u_gg": (800.0, 0.0, 40.0, 40.0), "u_cap": (0.0, 300.0, 40.0, 40.0),
             "u_nh": (300.0, 0.0, 40.0, 40.0)}
    pins = {"u_gg": {"g_v": {"0": (800.0, 0.0)}, "g_c": {"0": (800.0, 2.0)}, "g": {"0": (824.0, 0.0)}, "n_rh": {"0": (800.0, 30.0)}},
            "u_xr": {"eg_v": {"0": (0.0, 0.0)}, "eg_c": {"0": (0.0, 2.0)}, "eg_d": {"0": (0.0, 0.0)},
                     "cfg_v": {"0": (0.0, 40.0)}, "cfg_d": {"0": (0.0, 40.0)}, "x_scale": {"0": (40.0, 0.0)}},
            "u_cap": {"cfg_v": {"0": (430.0, 300.0)}, "cfg_d": {"0": (100.0, 300.0)}},
            "u_nh": {"o_r": {"0": (300.0, 30.0)}}}
    mk = lambda core, port, partner: dict(dir="in", core=core, port=port, partner=partner, bit_ranges=[[0, 0]], stages_existing=0, via=[])
    paths = [mk("u_xr", "eg_v", "u_gg.g_v"), mk("u_xr", "eg_c", "u_gg.g_c"), mk("u_xr", "eg_d", "u_gg.g"),
             mk("u_cap", "cfg_v", "u_xr.cfg_v"), mk("u_cap", "cfg_d", "u_xr.cfg_d"), mk("u_gg", "n_rh", "u_nh.o_r")]
    text = "module t;\n    a u_u_xr (.x(n));\n    b u_u_gg (.x(n));\n    c u_u_cap (.x(n));\n    d u_u_nh (.x(n));\nendmodule\n"
    import core_conns_from_bind as CC
    import relay_depth as RD
    monkeypatch.setattr(CC, "trace", lambda plan_, tn, text_, repo=None: {"paths": paths})
    monkeypatch.setattr(RD, "_pin_table", lambda hc, plan_dir: pins[hc["inst"]])
    mods = {"u_xr": "ot_s81sl_xrt1", "u_gg": "ot_s81sl_egg", "u_cap": "ot_s81sl_capc5r", "u_nh": "ot_s81sl_egn"}
    raw = {"partition_types": {"t": {"outline_um": [1200.0, 400.0], "hard_cores": [
        dict(inst=i, origin_um=[x, y], outline_um=[w, h], pins=1, module=mods[i]) for i, (x, y, w, h) in cores.items()]}}}
    rows, rep = RD.type_rows(raw, "t", text)
    got = {(r["inst"], r["port"]): r["D"] for r in rows}
    # OPUS-FIX-S81-SLICEC 11-20 HALF_FACE: egg (negedge out, 0.5) -> xr (negedge land, 0.5), 824 um: 3 stations; xr (OLAT
    # out, 0.1) -> cap 690 um: 2 (was 1)
    assert got == {("u_xr", "eg_v"): 3, ("u_xr", "eg_c"): 3, ("u_xr", "eg_d"): 3, ("u_cap", "cfg_v"): 2, ("u_cap", "cfg_d"): 2}
    assert len(rep["read_loops"]) == 1 and len(rep["unfixed"]) == 1 and rep["unfixed"][0]["port"] == "n_rh"
    assert RD._align_group("ot_s81sl_xrt1", "cfg_d") != RD._align_group("ot_s81sl_xrt1", "sw_d")
    assert RD._align_group("ot_s81sl_xrt1", "x_scale") is None and RD._align_group("ot_s81_sstn_base566", "g") is None


def test_half_face_stations():
    """OPUS-FIX-S81-SLICEC 11-20: weighted station count; full-cycle faces keep ceil(L / limit) - 1"""
    import relay_depth as RD
    for L in (100.0, 405.0, 406.0, 810.0, 811.0, 1300.0):
        assert RD.stations_needed(L, 405.0) == max(0, -(-int(L * 1000) // 405000) - 1)
    w = lambda m, side: RD._half_w(m, "p", side)
    assert w("ot_s81sl_xrt1", "out") == 0.1 and w("ot_s81sl_xrt1", "in") == 0.5 and w("ot_s81sl_egg", "out") == 0.5
    assert w("ot_s81sl_egg", "in") == 1.0 and w("ot_s81sl_capc5r", "out") == 1.0
    assert RD.stations_needed(923.2, 405.0, 0.1, 1.0) == 3 and RD.stations_needed(724.9, 405.0, 0.1, 1.0) == 2
    assert RD.stations_needed(800.9, 405.0, 0.5, 0.5) == 2 and RD.stations_needed(float("inf"), 405.0) == 0


def _lockup_vehicle(rows, **lk):
    """vehicle() with clock.core_input_lockup on core_sink.i (the QC NK pipe register + latch on the sink port)"""
    b, part = vehicle(rows)
    b.plan.setdefault("clock", {})["core_input_lockup"] = dict(dict(modules={"core_sink": ["i"]}, all=True, pipe=1), **lk)
    return b, part


@pytest.mark.parametrize("latch", [True, False])
@pytest.mark.parametrize("row", [{"inst": "u_y_rt_1", "D": 1}, {"inst": "u_sink", "port": "i", "side": "sink", "D": 1}])
def test_relay_stage_goes_before_the_lockup_pipe(row, latch):
    """QC-PLAN-R8 11-20 (cbf_q11 u_t_2_2.t_out -> d3 -> u_pc_nk_u_t_3_2_n_a, 1233 um): a relay_depth stage on a port that also
    carries the core_input_lockup pipe sits BEFORE u_pc_nk (the pc register stays the last stage, FIRM at the pin); before the fix
    the collapsed e ([pq] / [lk]) crashed with IndexError.  Declared per bit = relay D + npipe."""
    b, part = _lockup_vehicle([row], **({} if latch else {"latch_except": {"core_sink": ["i"]}}))
    text, _ = b.emit_type("src", part)
    xd = re.search(r"ot_dp_dly #\(\.W\(3\), \.D\(1\)\) (u_y_xd_\w+) \(\.clk\(clk\), \.d\(([^)]*)\), \.q\((\w+)\)\);", text)
    pc = re.search(r"ot_dp_dly #\(\.W\(3\), \.D\(1\)\) (u_pc_nk_\w+) \(\.clk\(clk\), \.d\(([^)]*)\), \.q\((\w+)\)\);", text)
    assert xd and pc and text.index(xd.group(0)) < text.index(pc.group(0))
    assert "w_u_y_rt_1_o" in xd.group(2)                                    # the relay stage reads the source wire
    assert pc.group(2) == f"{xd.group(3)}[2:0]" or pc.group(2) == xd.group(3)  # the pipe register reads the relay stage
    if latch:
        lk = re.search(r"ot_dp_lk #\(\.W\(3\)\) u_lk_nk_\w+ \(\.clk\(clk\), \.d\((\w+)\), \.q\((\w+)\)\);", text)
        assert lk and lk.group(1) == pc.group(3) and re.search(rf"\.i\({lk.group(2)}(\[2:0\])?\)", text)
    else:
        assert "u_lk_nk_" not in text and re.search(rf"\.i\({pc.group(3)}(\[2:0\])?\)", text)
    assert "u_pc_lp_" not in text
    rec = b.core_input_pipe
    assert rec["x.u_sink.i"] == 1 and all(rec[f"x.u_sink.i[{k}]"] == 2 for k in range(3))


def test_relay_stage_on_some_bits_of_a_lockup_port():
    b, part = _lockup_vehicle([{"inst": "u_sink", "port": "i", "side": "sink", "bits": [0, 1], "D": 2}])
    text, _ = b.emit_type("src", part)
    st = re.findall(r"ot_dp_dly #\(\.W\(2\), \.D\(1\)\) (u_y_xd_\w+) ", text)
    pc = re.search(r"(u_pc_nk_\w+) \(\.clk\(clk\), \.d\(([^)]*)\)", text)
    assert len(st) == 2 and all(text.index(s) < text.index(pc.group(1)) for s in st)
    assert "w_u_y_rt_1_o[2]" in pc.group(2)                                 # bit 2 goes straight into the pipe register
    rec = b.core_input_pipe
    assert rec["x.u_sink.i[0]"] == rec["x.u_sink.i[1]"] == 3 and "x.u_sink.i[2]" not in rec


def test_lockup_port_without_relay_rows_unchanged():
    """no relay_depth row: the lockup emission is the pre-fix text (pc then latch, no u_y_xd_)"""
    b, part = _lockup_vehicle([])
    text, _ = b.emit_type("src", part)
    assert "u_y_xd_" not in text
    assert re.search(r"u_pc_nk_u_sink_i \(\.clk\(clk\), \.d\(w_u_y_rt_1_o\[2:0\]\), \.q\(pq_u_sink_i\)\);", text)
    assert re.search(r"u_lk_nk_u_sink_i \(\.clk\(clk\), \.d\(pq_u_sink_i\), \.q\(lk_u_sink_i\)\);", text)
    assert b.core_input_pipe == {"x.u_sink.i": 1}


def test_link_pipe_after_collapsed_lockup_expands_per_bit():
    """generic collapse bug: a core_link_pipe on bits of a lockup port indexed e = [lk] (IndexError / whole bus on bit 0)"""
    b, part = _lockup_vehicle([])
    b.plan["clock"]["core_link_pipe"] = {"all": True, "modules": {"core_sink": {"i": {"D": 1, "bits": [1, 2]}}}}
    text, _ = b.emit_type("src", part)
    lp = re.search(r"u_pc_lp_\w+ \(\.clk\(clk\), \.d\(([^)]*)\), \.q\((\w+)\)\);", text)
    assert lp and lp.group(1) == "lk_u_sink_i[2:1]"
    assert re.search(rf"\.i\(\{{{lp.group(2)}\[1:0\], ?lk_u_sink_i\[0\]\}}\)", text)


def test_chain_hook_takes_relay_stages_and_relay_mid_leaves_them():
    d = Path(__file__).resolve().parent
    chain = (d / "core_input_chain.tcl").read_text()
    assert "u_pd[0-9]+_|u_y_xd_)} $nm]" in chain
    rm = (d / "relay_mid.tcl").read_text()
    assert "proc rm_feeds_pc" in rm and "dict unset rm_grp $g" in rm
