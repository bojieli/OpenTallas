"""BIND-STREAM-LAUNCH 11-24 (COORD): wave option bind_stream_launch (ON for s81 / qwen_compute / qwen_kvsys): a running strict bind
of record passes the gen-host check by its bind dir and the item's bind stage by the type's own record (bind_stream.py check)"""
import json
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "die_plan"))
import kit_wave as K  # noqa: E402
import bind_stream as BS  # noqa: E402
import kit_topology as KT  # noqa: E402


def cfg(bind):
    return {"dies": {d: {"gen_host": "epyc9", "gen_hosts": [], "event": "e", "src": "/s/src", "plan": "/p/plan.json",
                         "kit_rtl": {"mode": "bind", "bind_out": str(bind), "asbuilt": "/x/asb.json"}}
                     for d in ("qwen_kvsys", "s81", "qwen_compute", "s81_head", "hbm")}}


def test_option_default_on_for_three_dies(tmp_path):
    c = cfg(tmp_path)
    assert [d for d in c["dies"] if K.bind_stream_on(c, d)] == ["qwen_kvsys", "s81", "qwen_compute"]
    c["dies"]["s81"]["bind_stream_launch"] = False
    c["dies"]["hbm"]["bind_stream_launch"] = True
    assert not K.bind_stream_on(c, "s81") and K.bind_stream_on(c, "hbm")
    c2 = cfg(tmp_path); c2["bind_stream_launch"] = False
    assert not K.bind_stream_on(c2, "qwen_kvsys")


def test_running_bind_dir_needs_provenance_not_report(tmp_path):
    b = tmp_path / "bind"; b.mkdir()
    (b / "provenance_bind.json").write_text("{}")             # a running bind: no bind.f / bind_report.json yet
    c = cfg(b)
    K._BIND_FILES_CACHE.clear(); K._BIND_NAMED_CACHE.clear()
    _, files = K.src_inputs(c, "s81")
    assert str(b / "provenance_bind.json") in files and str(b / "bind_report.json") not in files
    _, files = K.src_inputs(c, "s81_head")                       # option off: unchanged
    assert str(b / "bind_report.json") in files


def _bind(tmp_path):
    raw = dict(partition_types={'ta': dict(reset=dict(depth=3), buses=[]), 'tb': dict(reset=dict(depth=2), buses=[])},
               reset=dict(root='r'), lanes=[], ports=[])
    plan = tmp_path / 'plan.json'; plan.write_text(json.dumps(raw))
    ab = tmp_path / 'ab.json'; ab.write_text('{}')
    out = tmp_path / 'bind'; (out / 'rtl').mkdir(parents=True)
    (out / 'rtl' / 'bind_cells.sv').write_text('//\n')
    ctx = BS.start(out, KT.bind_receipt(raw, str(ab), plan_path=plan), plan, str(ab))
    f = out / 'rtl' / 'm_ta.sv'; f.write_text('module m_ta; endmodule\n')
    BS.write_type(ctx, 'ta', 'm_ta', 1, [f], [], [], out / 'rtl' / 'bind_cells.sv', instance_params={'u_a': ''})
    return raw, plan, ab, out


def test_stage_check_per_type(tmp_path):
    raw, plan, ab, out = _bind(tmp_path)
    assert BS.main(["check", "--bind-out", str(out), "--type", "ta", "--plan", str(plan), "--asbuilt", str(ab)]) == 0
    assert BS.main(["check", "--bind-out", str(out), "--type", "tb", "--plan", str(plan), "--asbuilt", str(ab)]) == 3
    other = tmp_path / 'other.json'; other.write_text(json.dumps(raw, indent=1))
    rc, line = BS.launch_check(out, 'ta', other, str(ab))
    assert rc == 3 and 'BIND_STALE' in line
    rc, line = BS.launch_check(out, 'ta', plan, str(tmp_path / 'plan.json'))   # another as-built
    assert rc == 3
    time.sleep(0.01)
    (out / 'bind_report.json').write_text(json.dumps(dict(errors=['EMIT tb: gap'])))       # bind ended with errors
    assert BS.launch_check(out, 'ta', plan, str(ab)) == (3, 'BIND errors 1')
    (out / 'bind_report.json').write_text(json.dumps(dict(errors=[])))
    assert BS.launch_check(out, 'ta', plan, str(ab)) == (0, 'BIND errors 0')


def test_spec_carries_option_into_stage_command():
    src = (Path(__file__).resolve().parent / "kit_wave.py").read_text()
    assert 'if sp.get("bind_stream_launch"):' in src and "check --bind-out {q(bind)} --type {q(T)} --plan {q(plan)}" in src
