"""TOOLSTALE-GATE-RT-1123 (COORD 16:3x): every ot-run unit starts with OT_TOOLSTALE_RT pinned to the rt/<sha> rt/current named at unit start, so a
TOOLSTALE / plan_gate_pre --ref-tools auto check hours later compares against that rt, not the one rt/current moved to."""
import importlib.machinery
import importlib.util
import os
import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent


def load():
    loader = importlib.machinery.SourceFileLoader("ot_run_rt_pin", str(HERE / "ot-run"))
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(m)
    return m


def _sh(frag, env=None):
    return subprocess.run(["bash", "-c", frag + 'echo "ENV=${OT_TOOLSTALE_RT:-}"; bash -c \'echo "CHILD=${OT_TOOLSTALE_RT:-}"\''],
                          capture_output=True, text=True, env=dict(env or {}, PATH=os.environ["PATH"]))


def test_unit_pins_the_current_rt_at_start_and_children_inherit_it(tmp_path):
    m = load()
    for sha in ("aaaa11112222", "bbbb33334444"):
        (tmp_path / sha / "tools").mkdir(parents=True)
    (tmp_path / "current").symlink_to(tmp_path / "aaaa11112222")
    m.RT_PIN_ROOTS = (str(tmp_path / "missing"), str(tmp_path))
    r = _sh(m.rt_pin_sh("otrun-x-1-2", caller=""), env={"OT_TOOLSTALE_RT": "/stale/login/value"})
    want = str((tmp_path / "aaaa11112222").resolve())
    assert f"ENV={want}" in r.stdout and f"CHILD={want}" in r.stdout
    assert m.rt_pin_line(r.stderr.strip(), "otrun-x-1-2") == (want, "current")
    assert m.rt_pin_line(r.stderr.strip(), "otrun-other") is None


def test_caller_pin_is_passed_through_unchanged(tmp_path, monkeypatch):
    m = load()
    monkeypatch.setenv("OT_RT_CURRENT", "/srv/x/claude/rt/dddd77778888")     # a caller's global rt_pin is not the TOOLSTALE pin
    monkeypatch.setenv("OT_TOOLSTALE_RT", "/srv/x/claude/rt/cccc55556666")
    r = _sh(m.rt_pin_sh("t1"))
    assert "CHILD=/srv/x/claude/rt/cccc55556666" in r.stdout
    assert m.rt_pin_line(r.stderr.strip(), "t1") == ("/srv/x/claude/rt/cccc55556666", "caller")


def test_no_rt_leaves_it_unset_and_never_fails(tmp_path):
    m = load()
    m.RT_PIN_ROOTS = (str(tmp_path),)
    r = _sh(m.rt_pin_sh("t2", caller=""))
    assert r.returncode == 0 and "CHILD=\n" in r.stdout and r.stderr == ""


def test_remote_command_carries_the_pin_before_ot_heavy(monkeypatch):
    m = load()
    seen = {}

    class P:
        stderr = iter([b"OT_RUN_RTPIN TAG /srv/opentallas-scratch2/claude/rt/aaaa11112222 current\n"])

        def __init__(self, argv, **kw):
            seen["remote"] = argv[-1]
            tag = argv[-1].split("--tag ")[1].split()[0]
            self.stderr = iter([f"OT_RUN_RTPIN {tag} /srv/opentallas-scratch2/claude/rt/aaaa11112222 current\n".encode()])

        def wait(self):
            return 255

        def kill(self):
            pass
    monkeypatch.delenv("OT_TOOLSTALE_RT", raising=False)
    monkeypatch.setattr(m.subprocess, "Popen", P)
    monkeypatch.setattr(m, "_OTS", None)
    m.run("h", 1, ["true"], quiet=True)
    r = seen["remote"]
    assert r.index("export OT_TOOLSTALE_RT=") < r.index("/usr/local/bin/ot-heavy")
    assert "OT_RT_CURRENT" not in r          # the global tool-root variable is never set by the scheduler (source-tree PRE runs)
