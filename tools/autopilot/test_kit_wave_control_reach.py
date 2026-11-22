"""S1 (FABLE-FLOW-0800): a driver of an older rt reads its CONTROL scripts (geom_check.sh, the geom gate, the chain goal) from rt/current
at each stage start; result tools stay pinned; every difference is logged."""
import hashlib
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit_wave as K  # noqa: E402


def _rt(tmp_path, sha, gate_src=None, geom_check=b"#!/bin/bash\nexit 0\n"):
    d = tmp_path / "rt" / sha / "tools" / "autopilot"
    d.mkdir(parents=True)
    src = (HERE / "kit_wave.py").read_text()
    if gate_src:
        src = src.replace('def geom_gate(line, waived=None, advisory=True):\n',
                          'def geom_gate(line, waived=None, advisory=True):\n' + gate_src, 1)
    (d / "kit_wave.py").write_text(src)
    for f in HERE.glob("*.py"):
        if f.name != "kit_wave.py" and not f.name.startswith("test_") and f.name not in K.GEOM_TOOL_FILES:
            (d / f.name).symlink_to(f)
    (tmp_path / "rt" / sha / "tools" / "die_plan").symlink_to(HERE.parent / "die_plan")
    for n in K.GEOM_TOOL_FILES:
        (d / n).write_bytes((HERE / n).read_bytes() if n != "geom_check.sh" else geom_check)
    return d


def _current(tmp_path, sha):
    cur = tmp_path / "rt" / "current"
    if cur.is_symlink():
        cur.unlink()
    cur.symlink_to(tmp_path / "rt" / sha)


def test_control_root_is_rt_current_resolved_now(tmp_path):
    old = _rt(tmp_path, "aaa")
    new = _rt(tmp_path, "bbb")
    _current(tmp_path, "bbb")
    assert K.control_root(env={}, own=old) == new.resolve()
    assert K.control_root(env={}, own=new) is None                      # the driver IS rt/current
    assert K.control_root(env={"OT_CONTROL_ROOT": "0"}, own=old) is None
    assert K.control_root(env={}, own=tmp_path / "x" / "y") is None     # not under an rt dir


def test_geom_check_comes_from_rt_current_result_tools_stay_pinned(tmp_path, capsys):
    old = _rt(tmp_path, "aaa", geom_check=b"#!/bin/bash\nexit 1\n")
    new = _rt(tmp_path, "bbb", geom_check=b"#!/bin/bash\nexit 0\n")
    (new / "geom_rules.py").write_text("# newer result tool\n")
    K.CONTROL_REACH.clear()
    calls = []

    def run(tag, argv, idempotent=False):
        calls.append(tag)
        if tag == "geom_tools_copy":
            shutil.copytree(argv[-2].rstrip("/"), argv[-1].rstrip("/"), dirs_exist_ok=True)
        if tag == "geom_tools_verify":
            return 0, "KW_GEOM_TOOLS_OK " + argv[-1].split("KW_GEOM_TOOLS_OK ")[1][:16]
        return 0, ""

    out = tmp_path / "attempt"
    out.mkdir()
    staged = Path(K.stage_geom_tools(out, str(tmp_path / "geom"), "localhost", "localhost", run, tool_root=old, control=new))
    assert (staged / "geom_check.sh").read_bytes() == b"#!/bin/bash\nexit 0\n"             # control: rt/current
    assert (staged / "geom_rules.py").read_bytes() == (old / "geom_rules.py").read_bytes()  # result: pinned
    txt = capsys.readouterr().out
    assert "KW_CONTROL_REACH stage=geom geom_check.sh" in txt and "used=current" in txt
    assert "KW_FIX_NOT_REACHED stage=geom geom_rules.py" in txt
    assert [r["name"] for r in K.CONTROL_REACH] == ["geom_check.sh"]


def test_geom_gate_is_called_from_rt_current_when_it_differs(tmp_path, monkeypatch, capsys):
    _rt(tmp_path, "bbb", gate_src='    return "PASS-COND", [], "GATE-FROM-CURRENT"\n')
    monkeypatch.setenv("OT_CONTROL_ROOT", str(tmp_path / "rt" / "bbb" / "tools" / "autopilot"))
    K.CONTROL_REACH.clear()
    line = "AP_AUTO_GEOM AUTO-GEOM FAIL x fill=FAIL(0.01)"
    v = K.control_call("geom", "geom_gate", (line, None, False), K.geom_gate)
    assert v == ["PASS-COND", [], "GATE-FROM-CURRENT"]
    assert K.geom_gate(line, None, False)[2] != "GATE-FROM-CURRENT"       # the driver's own copy answers differently
    assert K.CONTROL_REACH and K.CONTROL_REACH[0]["used"] == "current"


def test_same_source_or_broken_current_falls_back_to_driver(tmp_path, monkeypatch, capsys):
    d = _rt(tmp_path, "ccc")
    monkeypatch.setenv("OT_CONTROL_ROOT", str(d))
    K.CONTROL_REACH.clear()
    seen = []
    assert K.control_call("geom", "geom_gate", ("l", None, True), lambda *a: seen.append(a) or ("X", [], "")) == ("X", [], "")
    assert seen and not K.CONTROL_REACH                                    # identical source: no subprocess, no note
    (d / "kit_wave.py").write_text((d / "kit_wave.py").read_text().replace(
        'def geom_gate(line, waived=None, advisory=True):\n', 'def geom_gate(line, waived=None, advisory=True):\n    raise SystemExit(3)\n', 1))
    assert K.control_call("geom", "geom_gate", ("l", None, True), lambda *a: ("LOCAL", [], "")) == ("LOCAL", [], "")
    assert "used=driver" in capsys.readouterr().out
