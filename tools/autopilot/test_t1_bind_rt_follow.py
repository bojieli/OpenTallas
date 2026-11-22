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
    assert KW.bind_rt_follow(cfg, "s81", cur)["tools_rt"] == a
    assert KW.bind_rt_follow(cfg, "s81", {"tools_rt": a, "tools_sha": "a" * 12})["tools_rt"] == a      # already fits


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
