import json
"""T1 (WAVE-OPS-R1 11-22, FABLE-FLOW-0800): gen runs on the rt the bind of record was made on; a tool skew never opens a class breaker."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import flow_guard as FG  # noqa: E402
import kit_wave as KW  # noqa: E402


def snap(root, name, anchor):
    d = Path(root) / name
    (d / "tools/autopilot").mkdir(parents=True)
    (d / "tools/die_plan").mkdir(parents=True)
    (d / "tools/autopilot/rt_launch_tree.sh").write_text("#\n")
    (d / "tools/die_plan/reset_anchor.py").write_text(anchor)
    return str(d)


def test_launch_follows_the_bind_rt(tmp_path, monkeypatch):
    a = snap(tmp_path, "a" * 12, "v1")
    b = snap(tmp_path, "b" * 12, "v2")          # the scheduler's current rt: other generators
    stamp = {"tools_sha": "", "generators": KW.rt_generator_hashes(a)}
    monkeypatch.setattr(KW, "BIND_STAMP_LOADER", lambda cfg, die, bo: stamp)
    cfg = {"dies": {"s81": {"kit_rtl": {"mode": "bind", "bind_out": "/x/bind1"}}}}
    cur = {"tools_rt": b, "tools_sha": "b" * 12}
    # BIND-PIN-1124: the kit runs the newest rt b, only the bind's differing generators pinned from a (by content sha)
    f = KW.bind_rt_follow(cfg, "s81", cur)
    assert f["tools_rt"] == b and f["gen_pins"]["rt"] == a
    assert f["gen_pins"]["files"] and all(stamp["generators"][n] == h for n, h in f["gen_pins"]["files"].items())
    assert KW.bind_rt_follow(cfg, "s81", {"tools_rt": a, "tools_sha": "a" * 12})["tools_rt"] == a      # already fits
    monkeypatch.setenv("OT_BIND_PIN", "0")                                                              # the old rule: the whole bind rt
    assert KW.bind_rt_follow(cfg, "s81", dict(cur))["tools_rt"] == a


def test_no_fitting_snapshot_keeps_current_and_no_stamp_is_ignored(tmp_path, monkeypatch):
    b = snap(tmp_path, "b" * 12, "v2")
    cfg = {"dies": {"s81": {"kit_rtl": {"mode": "bind", "bind_out": "/x/bind2"}}}}
    cur = {"tools_rt": b, "tools_sha": "b" * 12}
    monkeypatch.setattr(KW, "BIND_STAMP_LOADER", lambda cfg, die, bo: {"generators": {"reset_anchor.py": "0" * 64}})
    assert KW.bind_rt_follow(cfg, "s81", cur) == cur
    monkeypatch.setattr(KW, "BIND_STAMP_LOADER", lambda cfg, die, bo: None)
    assert KW.bind_rt_follow(cfg, "s81", cur) == cur
    cfg["dies"]["s81"]["kit_rtl"] = {"mode": "tree"}
    assert KW.bind_rt_follow(cfg, "s81", cur) == cur


def test_toolskew_fail_never_opens_a_breaker():
    st = {}
    for i in range(12):
        FG.record_fail(st, "s81", f"leaf_t{i}", "FLOW", "BIND-GEN-TOOLSKEW: the bind of record ran with other generators", stage="bind_toolskew")
    assert not FG.fg_state(st)["open"]
    for i in range(12):
        FG.record_fail(st, "s81", f"x{i}", "FLOW", "other tcl error", stage="place")
    assert FG.fg_state(st)["open"]


def test_launch_tree_pins_bind_generators_by_sha(tmp_path):
    """BIND-PIN-1124: rt_launch_tree.sh overlays the pinned generators from the pin rt, each sha-checked; a wrong sha composes nothing"""
    import hashlib as _h, subprocess as _sp
    sh = str(Path(KW.__file__).resolve().parent / "rt_launch_tree.sh")
    src = tmp_path / "tree"; (src / "physical").mkdir(parents=True)
    new, old = tmp_path / "rt" / ("b" * 12), tmp_path / "rt" / ("a" * 12)
    for d, v in ((new, "new"), (old, "old")):
        (d / "tools" / "die_plan").mkdir(parents=True)
        (d / "tools" / "die_plan" / "reset_tree.py").write_text(v)
        (d / "tools" / "die_plan" / "gen_phys.py").write_text(v)
    h = _h.sha256(b"old").hexdigest()
    L = tmp_path / "L1"
    r = _sp.run(["bash", sh, str(src), str(new), str(L), str(old), f"reset_tree.py={h}"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert (L / "tools" / "die_plan" / "reset_tree.py").read_text() == "old"      # pinned: the bind's generator
    assert (L / "tools" / "die_plan" / "gen_phys.py").read_text() == "new"        # every other tool: the newest rt
    assert (new / "tools" / "die_plan" / "reset_tree.py").read_text() == "new"    # the rt snapshot itself untouched
    assert json.loads((L / ".rt_launch_ok").read_text())["pins"] == {"reset_tree.py": h}
    r = _sp.run(["bash", sh, str(src), str(new), str(tmp_path / "L2"), str(old), "reset_tree.py=" + "0" * 64], capture_output=True, text=True)
    assert r.returncode == 97 and "pin reset_tree.py" in r.stderr and not (tmp_path / "L2").exists()
    sp = {"src": str(src), "tools_rt": str(new), "gen_pins": {"rt": str(old), "files": {"reset_tree.py": h}}}
    assert KW.sp_launch_path(sp) != KW.rt_launch_path(str(src), str(new)) and "+pin" in KW.sp_launch_path(sp)
    assert "reset_tree.py=" + h in KW.rt_tree_cmd(sp)
