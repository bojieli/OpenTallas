"""CARRY-FWD-1125 (COORD 05:4x, KV-SENDER-SKEW): a whole-bind-rt fallback keeps the newest bind_stream snapshot fix (d53d2f5627)."""
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402

NEW = "def _ended_snapshot(out, tn):\n    return False\n\ndef launch_check(b, t, p, a=None):\n    return 0, ''\n"
OLD = "def launch_check(b, t, p, a=None):\n    return 0, ''\n"


def _rt(root, name, bs, user="import bind_stream as BS\nBS.launch_check(1, 2, 3)\n"):
    d = root / name / "tools" / "die_plan"
    d.mkdir(parents=True)
    (d / "bind_stream.py").write_text(bs)
    (d / "kit_snap_user.py").write_text(user)
    return str(root / name)


def test_carry_pins_brings_the_snapshot_fix(tmp_path):
    new, old = _rt(tmp_path, "rtnew", NEW), _rt(tmp_path, "rtold", OLD)
    cp = KW.carry_pins(new, old)
    assert cp["rt"] == new and cp["sha"] == "rtnew" and cp["carry"]
    assert cp["files"] == {"bind_stream.py": hashlib.sha256(NEW.encode()).hexdigest()}
    assert KW.carry_pins(new, _rt(tmp_path, "rtfixed", NEW)) is None              # the fallback rt already has the fix
    assert KW.carry_pins(old, _rt(tmp_path, "rtold2", OLD)) is None               # nothing newer to carry


def test_carry_pins_refuses_an_api_gap(tmp_path):
    new = _rt(tmp_path, "rtnew", NEW)
    old = _rt(tmp_path, "rtold", OLD, user="import bind_stream as BS\nBS.old_only_helper()\n")
    assert KW.carry_pins(new, old) is None                                        # old rt's modules call a name the new file lacks


def test_off_switch(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_CARRY_PIN", "0")
    assert KW.carry_pins(_rt(tmp_path, "a", NEW), _rt(tmp_path, "b", OLD)) is None


def test_bind_rt_follow_whole_rt_carries(tmp_path, monkeypatch):
    new, old = _rt(tmp_path, "rtnew", NEW), _rt(tmp_path, "rtold", OLD)
    cfg = {"dies": {"d": {"kit_rtl": {"mode": "bind", "bind_out": "/b"}}}}
    monkeypatch.setattr(KW, "load_bind_stamp", lambda c, d, b: {"generators": {"reset_tree.py": "x"}})
    monkeypatch.setattr(KW, "stamp_diff", lambda st, g: ["reset_tree.py"])
    monkeypatch.setattr(KW, "rt_fit_for_stamp", lambda st, root, rt: (old, "rtold"))
    monkeypatch.setattr(KW, "bind_pins", lambda *a: None)                         # BIND-PIN refused (api gap) -> whole bind rt
    KW.BIND_RT_FIT.clear()
    f = KW.bind_rt_follow(cfg, "d", {"tools_rt": new, "tools_sha": "rtnew"})
    assert f["tools_rt"] == old and f["gen_pins"]["files"] == {"bind_stream.py": hashlib.sha256(NEW.encode()).hexdigest()}
