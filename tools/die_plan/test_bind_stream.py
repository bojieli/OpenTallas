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
