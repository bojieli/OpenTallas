"""BIND-STREAM-LAUNCH 11-24: per-type stream records of a running bind (bind_stream.py) and their readers
(kit_topology.bind_matches, bind.py kit-rtl).  python3 -m pytest tools/die_plan/test_bind_stream.py"""
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind_stream as BS  # noqa: E402
import kit_topology as K  # noqa: E402


def fixture(tmp_path):
    raw = dict(partition_types={
        'ta': dict(clock=dict(taps=[dict(x=1, y=2)]), reset=dict(depth=3), buses=[]),
        'tb': dict(clock=dict(taps=[dict(x=5, y=6)]), reset=dict(depth=2), buses=[]),
    }, reset=dict(root='r'), lanes=[], ports=[])
    plan = tmp_path / 'plan.json'
    plan.write_text(json.dumps(raw))
    ab = tmp_path / 'asbuilt.json'
    ab.write_text('{}')
    out = tmp_path / 'bind'
    (out / 'rtl').mkdir(parents=True)
    (out / 'rtl' / 'bind_cells.sv').write_text('// cells\n')
    ctx = BS.start(out, K.bind_receipt(raw, str(ab), plan_path=plan), plan, str(ab))
    return raw, plan, ab, out, ctx


def emit(out, ctx, tn):
    f = out / 'rtl' / f'm_{tn}.sv'
    f.write_text(f'module m_{tn}; endmodule\n')
    return BS.write_type(ctx, tn, f'm_{tn}', 1, [f], ['/lib/a.sv'], [], out / 'rtl' / 'bind_cells.sv')


def test_stream_record_stands_in_for_end_receipt(tmp_path):
    raw, plan, ab, out, ctx = fixture(tmp_path)
    assert not (out / 'native_topology.json').exists()
    assert not K.bind_matches(raw, 'ta', out, str(ab), plan)          # not emitted yet: still stale
    emit(out, ctx, 'ta')
    assert K.bind_matches(raw, 'ta', out, str(ab), plan)              # its own final record: kit-ready
    assert not K.bind_matches(raw, 'tb', out, str(ab), plan)          # the other type waits for its own record
    rep = BS.report(out, 'ta')
    assert rep['types'] == {'ta': dict(module='m_ta', instances=1)} and rep['n_errors'] == 0
    assert rep['bind_f'][0] == '/lib/a.sv' and rep['bind_f'][-1].endswith('m_ta.sv')


def test_same_checks_per_type(tmp_path, monkeypatch):
    raw, plan, ab, out, ctx = fixture(tmp_path)
    emit(out, ctx, 'ta')
    # a changed type topology is still stale (same field compare as the end receipt)
    raw2 = json.loads(json.dumps(raw)); raw2['partition_types']['ta']['buses'] = [dict(name='x', dir='in', width=1)]
    plan2 = tmp_path / 'plan2.json'; plan2.write_text(json.dumps(raw2))
    assert not K.bind_matches(raw2, 'ta', out, str(ab), plan2)
    # another as-built
    ab2 = tmp_path / 'ab2.json'; ab2.write_text('{"x":1}')
    assert not K.bind_matches(raw, 'ta', out, str(ab2), plan)
    # the context plan must have the bind's plan sha256 (a copy of the same bytes elsewhere is fine)
    same = tmp_path / 'copy' / 'plan.json'; same.parent.mkdir(); same.write_bytes(plan.read_bytes())
    assert K.bind_matches(raw, 'ta', out, str(ab), same)
    other = tmp_path / 'plan3.json'; other.write_text(json.dumps(raw, indent=2))   # same content, other bytes
    why = []
    assert BS.receipt(out, 'ta', other, why) is None and 'plan sha256' in why[-1]
    assert not K.bind_matches(raw, 'ta', out, str(ab), other)


def test_record_refused_when_changed_withdrawn_or_bind_ended(tmp_path):
    raw, plan, ab, out, ctx = fixture(tmp_path)
    emit(out, ctx, 'ta'); emit(out, ctx, 'tb')
    (out / 'rtl' / 'm_tb.sv').write_text('module m_tb; wire changed; endmodule\n')
    why = []
    assert BS.records(out, 'tb', why) == [] and 'file changed' in why[-1]
    assert not K.bind_matches(raw, 'tb', out, str(ab), plan)
    assert BS.finish(ctx, ['EMIT ta: port x unbound', 'TIED_TOTAL 3 bits']) == ['ta']
    assert not K.bind_matches(raw, 'ta', out, str(ab), plan)
    rec = json.loads((out / BS.DIR / 'ta.json').read_text())
    assert rec['final'] is False and rec['withdrawn']
    # once bind_report.json is written the finished bind decides (no end receipt = stale, as before)
    emit(out, ctx, 'tb')
    assert K.bind_matches(raw, 'tb', out, str(ab), plan)
    time.sleep(0.01)
    (out / 'bind_report.json').write_text('{"n_errors": 1, "types": {}}')
    os.utime(out / 'bind_report.json', None)
    assert BS.newer_than_context(out) is None and not K.bind_matches(raw, 'tb', out, str(ab), plan)


def test_new_bind_clears_old_records(tmp_path):
    raw, plan, ab, out, ctx = fixture(tmp_path)
    emit(out, ctx, 'ta')
    ctx2 = BS.start(out, K.bind_receipt(raw, str(ab), plan_path=plan), plan, str(ab))
    assert not (out / BS.DIR / 'ta.json').exists() and ctx2['run_id'] != ctx['run_id']
    emit(out, ctx, 'ta')                                                # a record of the earlier run: refused
    why = []
    assert BS.records(out, 'ta', why) == [] and ('other run' in why[-1] or 'other context' in why[-1])


def test_split_variants_all_final(tmp_path):
    raw, plan, ab, out, ctx = fixture(tmp_path)
    emit(out, ctx, 'ta__v0')
    assert len(BS.records(out, 'ta')) == 1
    emit(out, ctx, 'ta__v1')
    BS.finish(ctx, ['EMIT ta__v1: gap'])
    assert BS.records(out, 'ta') == []                                  # one withdrawn variant holds the type


# ---- end to end on examples/bind_tiny (Yosys)
EX = HERE / "examples" / "bind_tiny"
HAVE_YOSYS = bool(os.environ.get("OT_BIND_YOSYS")) or bool(shutil.which("docker"))


@pytest.mark.skipif(not HAVE_YOSYS, reason="no Yosys (OT_BIND_YOSYS) and no docker")
@pytest.mark.parametrize("jobs", ["1", "2"])
def test_tiny_bind_streams_and_kit_rtl_reads_stream(tmp_path, monkeypatch, jobs):
    import bind
    monkeypatch.setenv("OT_BIND_EMIT_J", jobs)
    plan = EX / "die_plan_lanes.json"
    out = tmp_path / "o"
    for c in ("elab", "bind"):
        assert bind.main([c, str(plan), "--out", str(out), "--mem", "4"]) == 0
    rep = json.loads((out / "bind_report.json").read_text())
    recs = {p.stem: json.loads(p.read_text()) for p in (out / BS.DIR).glob("*.json") if p.name != BS.CTX}
    assert set(recs) == set(rep["types"]) and all(r["final"] for r in recs.values())
    assert all(r["module"] == rep["types"][t]["module"] for t, r in recs.items())
    receipt = json.loads((out / "native_topology.json").read_text())
    assert json.loads((out / BS.DIR / BS.CTX).read_text())["receipt"] == receipt   # the stream carries the end receipt
    # the bind ended: the stream is not read
    assert BS.newer_than_context(out) is None
    # the same OUT as it was while the bind ran (before the end files): kit_topology + kit-rtl read the type's record
    for n in ("bind_report.json", "native_topology.json", "bind.f"):
        (out / n).rename(tmp_path / n)
    (out / BS.DIR / BS.ENDED).rename(tmp_path / BS.ENDED)       # the end marker is an end file too (BIND-STREAM-ENDED)
    raw = json.loads(plan.read_text())
    tn = "bt_ta" if "bt_ta" in raw["partition_types"] else sorted(raw["partition_types"])[0]
    assert K.bind_matches(raw, tn, out, None, plan)
    topf = next((out / "rtl").glob("*_bound_top.sv"))
    top = topf.read_text()
    inst = re.findall(r"^\s*\w+ #\(.*?\) (\w+) \(", top, re.M)[0]
    # the record's instance parameters are exactly what the top passes (kit-rtl's bound_instance_params)
    for t, r in recs.items():
        assert r["instance_params"] == bind.bound_instance_params(out, raw["die"]["name"], r["module"]), t
    topf.rename(tmp_path / topf.name)                                   # a running bind has no die top yet
    kd = tmp_path / "kit"
    assert bind.main(["kit-rtl", str(plan), "--out", str(out), "--type", tn, "--instance", inst, "--kit", str(kd)]) == 0
    man = json.loads((kd / "kit_rtl.json").read_text())
    assert man["bind_stream"][tn]["run_id"] == recs[tn]["run_id"]
    fl = (kd / "kit_rtl.f").read_text().split()
    assert all(Path(f).is_file() for f in fl)
    # a type not emitted yet (record removed) is refused by kit-rtl with the stream reason
    (out / BS.DIR / f"{tn}.json").unlink()
    assert bind.main(["kit-rtl", str(plan), "--out", str(out), "--type", tn, "--instance", inst, "--kit", str(tmp_path / "k2")]) != 0


@pytest.mark.skipif(not HAVE_YOSYS, reason="no Yosys (OT_BIND_YOSYS) and no docker")
def test_scoped_bind_without_top_kits_per_type(tmp_path, monkeypatch):
    """COORD 11-24 (QC FWCPL2, KV PCPACK R3): a scoped (OT_BIND_ONLY_TYPES) strict bind emits no die top; kit-rtl takes the
    instance parameters from the type's own record, and kit_topology the receipt"""
    import bind
    plan = EX / "die_plan_lanes.json"
    raw = json.loads(plan.read_text())
    tn = "bt_ta" if "bt_ta" in raw["partition_types"] else sorted(raw["partition_types"])[0]
    out = tmp_path / "o"
    assert bind.main(["elab", str(plan), "--out", str(out), "--mem", "4"]) == 0
    monkeypatch.setenv("OT_BIND_ONLY_TYPES", tn)
    bind.main(["bind", str(plan), "--out", str(out), "--mem", "4"])
    rep = json.loads((out / "bind_report.json").read_text())
    assert rep["probe_only"]["emitted"] == [tn] and not list((out / "rtl").glob("*_bound_top.sv"))
    rec = json.loads((out / BS.DIR / f"{tn}.json").read_text())
    assert rec["final"] and rec["instance_params"]
    inst = sorted(rec["instance_params"])[0]
    kd = tmp_path / "kit"
    assert bind.main(["kit-rtl", str(plan), "--out", str(out), "--type", tn, "--instance", inst, "--kit", str(kd)]) == 0
    man = json.loads((kd / "kit_rtl.json").read_text())
    assert man["params"] == (rec["instance_params"][inst] or man["params"])


# ---- BIND-TYPE-RECEIPT 11-24 (COORD ruling): errors attributed to their types; clean types get the receipt
def test_attribute_errors_owner_rules():
    import bind
    known = {"svc_lo__t1", "iqf__t1", "seqhost__t1"}
    pt = {"u_rsv_00.u.u_att": {"svc_lo__t1"}, "u_iq.x": {"iqf__t1"}}
    tied = {("u_rsv_00.u.u_att", "iblk", "m"): [(1, "0", "literal")]}
    errs = ["UNDRIVEN_OPEN u_rsv_00.u.u_att.d[1] (ot_hdc, type svc_lo__t1): 1 input bit(s) ...",
            "TIED u_rsv_00.u.u_att.iblk[1] = 0 (literal)",
            "TIED_TOTAL 486192 tied bits on 2288 leaf pins",
            "EMIT iqf__t1: x_o writer START stage 6 needs finite xy_um"]
    ref, un = bind.attribute_errors(errs, known, pt, {}, tied)
    assert un == [] and set(ref) == {"svc_lo__t1", "iqf__t1"} and len(ref["svc_lo__t1"]) == 3
    ref, un = bind.attribute_errors(errs + ["LANE_CYCLES L7: bound 3 != latency table 2"], known, pt, {}, tied)
    assert un == ["LANE_CYCLES L7: bound 3 != latency table 2"]                   # names no type: blocks everything
    ref, un = bind.attribute_errors(["TIED_TOTAL 9 tied bits"], known, pt, {}, {("u_nowhere", "p", "m"): [(0, "0", "x")]})
    assert un and not ref                                                          # a tied pin no type owns: unattributed


def test_partial_receipt_refuses_only_attributed_types(tmp_path):
    raw, plan, ab, out, ctx = fixture(tmp_path)
    K.write_bind_receipt(raw, out, str(ab), plan_path=plan, refused={"tb": ["TIED x"]})
    (out / 'bind_report.json').write_text(json.dumps(dict(errors=["TIED x"], n_errors=1)))
    assert K.bind_matches(raw, 'ta', out, str(ab), plan) and not K.bind_matches(raw, 'tb', out, str(ab), plan)
    assert K.receipt_type_clean(out, 'ta', 'ta')[0] and not K.receipt_type_clean(out, 'tb', 'tb')[0]
    assert BS.launch_check(out, 'ta', plan, str(ab))[0] == 0 and BS.launch_check(out, 'tb', plan, str(ab))[0] == 3
    (out / 'native_topology.json').unlink()                                          # no receipt (unattributed): all refused
    assert BS.launch_check(out, 'ta', plan, str(ab))[0] == 3


@pytest.mark.skipif(not HAVE_YOSYS, reason="no Yosys (OT_BIND_YOSYS) and no docker")
def test_tiny_bind_with_type_errors_receipts_clean_types(tmp_path):
    import bind
    p = json.loads((EX / "die_plan.json").read_text())
    p["asbuilt"]["straps"] = []                                   # TIED on p0.u_b.id: errors owned by type ta only
    p["asbuilt"]["base"] = str(EX)
    plan = tmp_path / "die_plan.json"
    plan.write_text(json.dumps(p))
    out = tmp_path / "o"
    assert bind.main(["elab", str(plan), "--out", str(out), "--mem", "4"]) == 0
    bind.main(["bind", str(plan), "--out", str(out), "--mem", "4"])
    rep = json.loads((out / "bind_report.json").read_text())
    assert rep["n_errors"] and rep["type_receipt"]["n_unattributed"] == 0 and {t.split("__")[0] for t in rep["type_receipt"]["refused"]} == {"ta"}
    rec = json.loads((out / "native_topology.json").read_text())
    assert rec["partial"] and {t.split("__")[0] for t in rec["refused"]} == {"ta"}
    raw = json.loads(plan.read_text())
    assert K.bind_matches(raw, "ts", out, None, plan) and not K.bind_matches(raw, "ta", out, None, plan)
    assert bind.main(["kit-rtl", str(plan), "--out", str(out), "--type", "ts", "--kit", str(tmp_path / "k_ts")]) == 0
    assert bind.main(["kit-rtl", str(plan), "--out", str(out), "--type", "ta", "--instance", "A0", "--kit", str(tmp_path / "k_ta")]) != 0


def test_attribute_lane_define_and_tied_classes():
    """BIND-ATTR-CLASSES 11-24: LANE_ASBUILT -> lane endpoint types; LANE_ASBUILT_TOTAL -> all off-table lane owners;
    TYPE_DEFINE_CONFLICT -> outside + requesters; TIED_TOTAL owners by path prefix; NOEFFECT / LF_CS_DEPTH by token-1 type."""
    import bind
    known = {"lf__t1", "c__t1", "svc__t1", "kv__t1", "other"}
    pt = {"u_rsv_00.u.u_h4": {"svc__t1"}}
    errs = ["LANE_ASBUILT up_s_0S_L1: delivered 8 != latency table 5 (+3; src s_0S_L1.leafup_o0 ...)",
            "LANE_ASBUILT_TOTAL 1 of 947 lanes deliver off the latency table",
            "TYPE_DEFINE_CONFLICT added ['OT_X'] changes types outside at least one requesting scope: {\"kv__t1\": [\"u.v\"], ...",
            "TYPE_DEFINE_NOEFFECT svc__t1: OT_X BIND_IGNORED",
            "LF_CS_DEPTH lf__t1 pvs: plan 2 stage(s) (deepest row), bound RTL 1",
            "TIED u_rsv_00.u.u_h4.iblk[1] = 0 (literal)",
            "TIED_TOTAL 486192 tied bits on 2288 leaf pins"]
    tied = {("u_rsv_00.u.u_h4.sub", "iblk", "m"): [(1, "0", "")]}      # deeper than any owned cell: prefix walk
    ref, un = bind.attribute_errors(errs, known, pt, {}, tied, ("kv__t1",), define_requesters=("svc__t1",),
                                    lane_types={"up_s_0S_L1": ("lf__t1", "c__t1")})
    assert un == []
    assert set(ref) == {"lf__t1", "c__t1", "svc__t1", "kv__t1"}
    assert len(ref["c__t1"]) == 2 and len(ref["kv__t1"]) == 1
    _, un = bind.attribute_errors(errs[:2], known, pt, lane_types={})
    assert len(un) == 2                                                 # unknown lane: both stay unattributed (block all)


def test_attribution_inputs_reads_sidecars(tmp_path):
    import bind
    (tmp_path / "type_defines.json").write_text(json.dumps(dict(outside={"kv__t1": []}, added=["OT_X"],
        rows=[dict(type="svc__t1", define="OT_X"), dict(type="z", define="OT_Y")])))
    (tmp_path / "bind_lane_asbuilt.json").write_text(json.dumps(dict(lanes=[dict(lane="L", src_type="a", dst_type="b")])))
    kw = bind.attribution_inputs(tmp_path, ["TYPE_DEFINE_CONFLICT x", "LANE_ASBUILT L: d"])
    assert kw == dict(define_outside=("kv__t1",), define_requesters=("svc__t1",), lane_types={"L": ("a", "b")})


def test_type_strict_report_basis(tmp_path):
    """BIND-STREAM-SNAP-2: whole-unbound proof report: global for a clean bind, per-type for a stream record / clean partial receipt"""
    import bind
    out, kd = tmp_path / "o", tmp_path / "k"
    out.mkdir(); kd.mkdir()
    assert bind._type_strict_report(out, kd, "ta", "ta", {"n_errors": 0}, None) == out / "bind_report.json"
    p = bind._type_strict_report(out, kd, "ta", "ta", {"n_errors": 0}, {"stream_records": {"ta": {"run_id": "r"}}})
    d = json.loads(p.read_text())
    assert d["n_errors"] == 0 and d["proof"]["tied"] == 0 and d["basis"]["kind"] == "bind_stream_record"
    (out / "native_topology.json").write_text(json.dumps({"partial": True, "refused": {"tb": ["TIED x"]}}))
    d = json.loads(bind._type_strict_report(out, kd, "ta", "ta", {"n_errors": 3}, None).read_text())
    assert d["basis"]["kind"] == "partial_type_receipt" and d["basis"]["global_n_errors"] == 3
    with pytest.raises(ValueError):
        bind._type_strict_report(out, kd, "tb", "tb", {"n_errors": 3}, None)


def test_alive_pid_and_heartbeat(tmp_path, monkeypatch):
    """BIND-STREAM-FINAL: a stream is live while its bind runs (same-host pid runs bind.py, or a fresh heartbeat); a killed bind's
    records are refused by the launch check"""
    import socket
    out = tmp_path / "o"
    d = out / BS.DIR
    d.mkdir(parents=True)
    (d / BS.CTX).write_text(json.dumps(dict(run_id="20261124T000000-999999999-x", host=socket.gethostname(), pid=999999999)))
    why = []
    assert not BS.alive(out, why) and "heartbeat absent" in why[0]
    (d / BS.HEARTBEAT).touch()
    assert BS.alive(out)
    old = time.time() - 900
    os.utime(d / BS.HEARTBEAT, (old, old))
    assert not BS.alive(out)
    rc, line = BS.launch_check(out, "ta", tmp_path / "plan.json")
    assert rc == 3 and "void" in line


def test_pre_emit_errors_withhold_records(tmp_path):
    """BIND-STREAM-FINAL: an analyse-phase error naming a type withholds its record; the other types still stream"""
    import bind
    calls = []

    class B:
        _stream = dict(pre_refused=["ta"], hold_all=False, dir=str(tmp_path))
        types = {"ta": {"module": "m_a"}, "tb": {"module": "m_b"}}
        emit_gaps = []
        extra_lib = []

        def _emit_type_files(self, tn, ps, out, files):
            files.append(tmp_path / f"{tn}.sv")

        def instance_params(self, tn, ps):
            return {}
    old = BS.write_type
    BS.write_type = lambda ctx, tn, *a, **k: calls.append(tn)
    try:
        for tn in ("ta", "tb"):
            bind.Binder._emit_one(B(), tn, ["p"], tmp_path, [])
        B._stream["hold_all"] = True
        bind.Binder._emit_one(B(), "tb", ["p"], tmp_path, [])
    finally:
        BS.write_type = old
    assert calls == ["tb"]


def _inst_blocks(text):
    return {m.group(2): m.group(0) for m in re.finditer(r"(?ms)^    (\w+)(?: #\([^\n]*\))? (\w+) \(\n.*?\n    \);", text)}


@pytest.mark.skipif(not HAVE_YOSYS, reason="no Yosys (OT_BIND_YOSYS) and no docker")
def test_scoped_bind_writes_scoped_top_and_strap_files(tmp_path, monkeypatch):
    """BIND-SPEED-1124 #4 SCOPED-TOP (COORD 11-24): a --types bind writes OUT/probe_top/<die>_bound_top.sv with exactly the
    full bind's instance blocks of the emitted types, the strap / tie sidecars, and still no rtl/*_bound_top.sv"""
    import bind
    plan = EX / "die_plan_lanes.json"
    raw = json.loads(plan.read_text())
    full, sc = tmp_path / "full", tmp_path / "sc"
    for o in (full, sc):
        assert bind.main(["elab", str(plan), "--out", str(o), "--mem", "4"]) == 0
    monkeypatch.delenv("OT_BIND_ONLY_TYPES", raising=False)
    bind.main(["bind", str(plan), "--out", str(full), "--mem", "4"])
    ftop = next((full / "rtl").glob("*_bound_top.sv"))
    tn = "bt_ta" if "bt_ta" in raw["partition_types"] else sorted(raw["partition_types"])[0]
    monkeypatch.setenv("OT_BIND_ONLY_TYPES", tn)
    bind.main(["bind", str(plan), "--out", str(sc), "--mem", "4"])
    assert not list((sc / "rtl").glob("*_bound_top.sv"))
    stop = sc / "probe_top" / ftop.name
    po = json.loads((sc / "BIND_PROBE_ONLY.json").read_text())
    assert po["scoped_top"]["path"] == f"probe_top/{ftop.name}"
    fb, sb = _inst_blocks(ftop.read_text()), _inst_blocks(stop.read_text())
    assert sb and len(sb) == po["scoped_top"]["instances"] < len(fb)
    assert all(fb[k] == v for k, v in sb.items())
    for name in ("bind_tie_audit.json",):
        assert (sc / name).is_file() == (full / name).is_file()
    for f in (full / "rtl").glob("*.sv"):
        s = sc / "rtl" / f.name
        if s.exists():
            assert s.read_bytes() == f.read_bytes(), f.name


def test_ended_bind_snapshot_reads_report_not_mtimes(tmp_path, monkeypatch):
    """KV-A5t6 r8f64f1de3: a whole-OUT kit snapshot of an ended bind (blob mtimes: _context.json newer than bind_report.json)
    passes on its bind_report; a stream snapshot (own records only) still needs a live bind"""
    raw, plan, ab, out0, ctx = fixture(tmp_path)
    emit(out0, ctx, 'ta')
    emit(out0, ctx, 'tb')
    monkeypatch.setattr(BS, "alive", lambda out, why=None: (why.append("bind heartbeat absent") if why is not None else None) and False)
    snap = tmp_path / 'snaps' / 'x' / 'root'
    out = snap / 'b'
    shutil.copytree(out0, out)
    (snap.parent / 'MANIFEST.json').write_text('{}')
    (out / 'bind_report.json').write_text(json.dumps(dict(errors=[])))
    old = time.time() - 900
    os.utime(out / 'bind_report.json', (old, old))
    rc, line = BS.launch_check(out, 'ta', plan, ab)
    assert rc == 0 and line == 'BIND errors 0'
    (out / BS.DIR / 'tb.json').unlink()           # stream snapshot: own type only -> liveness still decides
    rc, line = BS.launch_check(out, 'ta', plan, ab)
    assert rc == 3 and 'heartbeat absent' in line
    shutil.rmtree(snap.parent)
    (out0 / 'bind_report.json').write_text(json.dumps(dict(errors=[])))
    os.utime(out0 / 'bind_report.json', (old, old))  # not a snapshot: mtimes still decide
    rc, line = BS.launch_check(out0, 'ta', plan, ab)
    assert rc == 3 and 'heartbeat absent' in line


def test_ended_marker_beats_snapshot_mtimes_for_scoped_bind(tmp_path, monkeypatch):
    """KV-SENDER-SKEW 11-25 (A5t6 kv3_pv_v6e probe): a whole-OUT snapshot of an ENDED probe-only bind holds one type record and
    blob mtimes (_context.json newer than bind_report.json); finish()'s _ended.json (same run_id) makes it read ended"""
    raw, plan, ab, out0, ctx = fixture(tmp_path)
    emit(out0, ctx, 'ta')
    BS.finish(ctx, [])
    assert not (out0 / BS.DIR / BS.ENDED).exists()     # finish withdraws only; the marker follows bind_report.json
    BS.mark_ended(ctx)
    e = json.loads((out0 / BS.DIR / BS.ENDED).read_text())
    assert e["run_id"] == ctx["run_id"]
    monkeypatch.setattr(BS, "alive", lambda out, why=None: (why.append("bind heartbeat absent") if why is not None else None) and False)
    snap = tmp_path / 'snaps' / 'x' / 'root'
    out = snap / 'b'
    shutil.copytree(out0, out)
    (snap.parent / 'MANIFEST.json').write_text('{}')
    (out / 'bind_report.json').write_text(json.dumps(dict(errors=[])))
    old = time.time() - 900
    os.utime(out / 'bind_report.json', (old, old))
    rc, line = BS.launch_check(out, 'ta', plan, ab)
    assert rc == 0 and line == 'BIND errors 0'
    # a marker of another run (stale) does not end the live stream
    (out / BS.DIR / BS.ENDED).write_text(json.dumps(dict(run_id="other")))
    rc, line = BS.launch_check(out, 'ta', plan, ab)
    assert rc == 3 and 'heartbeat absent' in line


def test_start_clears_old_end_marker(tmp_path):
    raw, plan, ab, out0, ctx = fixture(tmp_path)
    BS.mark_ended(ctx)
    assert (out0 / BS.DIR / BS.ENDED).is_file() and BS._live(out0) is None
    ctx2 = BS.start(out0, K.bind_receipt(raw, str(ab), plan_path=plan), plan, str(ab))
    assert not (out0 / BS.DIR / BS.ENDED).is_file() and BS._live(out0) is not None
