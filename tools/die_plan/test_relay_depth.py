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
    for bad in ([{"inst": "u_y_a_0", "D": 5}], [{"inst": "u_y_a_0"}], [{"D": 1}], [{"inst": "x", "D": 1, "zz": 1}]):
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
    """relay_depth rows -> bind_core_input_pipe.json must be acknowledged (compiler / TOK do not read it); no rows = no check"""
    import lane_asbuilt_latency as LAL
    rec = {"x.u_sink.i[0]": 2, "x.u_sink.i[1]": 2}
    (tmp_path / "bind_core_input_pipe.json").write_text(json.dumps(rec))
    off = {"partition_types": {"t": {}}}
    assert LAL.internal_pipe_check(off, tmp_path) == ([], {})
    on = {"partition_types": {"t": {"relay_depth": [{"inst": "u_y_a", "D": 2}]}}}
    errs, info = LAL.internal_pipe_check(on, tmp_path)
    assert len(errs) == 1 and "INTERNAL_PIPE_UNACKED" in errs[0] and info["cycles"] == 4 and info["sink_bits"] == 2
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
