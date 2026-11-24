"""EVENT-ENV-PREFLIGHT 11-24 (FABLE FLOW REVIEW #3/#4): one env file per plan event (ot_event_env.py) and the ot-run --event-env
queue-time preflight.  Cases come from the 02:00-04:52 DIED census: lk_ES0's OT_PLAN_GATE_SKIP under a PRE=warn event, inputs present
on only one host, rt pins named by hand."""
import importlib.machinery
import importlib.util
import os
import pathlib
import subprocess
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ot_event_env as E  # noqa: E402
import ot_deathclass as D  # noqa: E402

GOOD = """# S81 J9 event (example)
OT_EVENT=S81-J9
OT_EVENT_RT=de23411d9e49
OT_EVENT_INPUTS=/srv/opentallas-scratch2/claude/s81-j9/bind,/srv/opentallas-scratch2/claude/s81-j9/tree
export OT_PLAN_GATE_PRE=warn
OT_PLAN_GATE_BASELINE='/srv/opentallas-scratch2/claude/s81-allfix-int/inputs/plan_h2_2249.json'
OT_PGCAP=1
"""


def load_run():
    loader = importlib.machinery.SourceFileLoader("ot_run_event_env", str(HERE / "ot-run"))
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(m)
    return m


def test_parse_good_file_and_unit_env():
    ev = E.parse(GOOD)
    assert ev["OT_PLAN_GATE_PRE"] == "warn" and ev["OT_PLAN_GATE_BASELINE"].endswith("plan_h2_2249.json")
    assert E.inputs(ev) == ["/srv/opentallas-scratch2/claude/s81-j9/bind", "/srv/opentallas-scratch2/claude/s81-j9/tree"]
    keys = [k for k, _ in E.unit_env(ev)]
    assert "OT_PGCAP" in keys and "OT_EVENT" in keys and "OT_EVENT_INPUTS" not in keys and "OT_RUN_PREFLIGHT" not in keys
    assert E.mode(ev, "") == "fail" and E.mode(None, "") == "warn" and E.mode(ev, "warn") == "warn"
    assert E.rt_candidates("de23411d9e49", roots=("/a/rt", "/b/rt")) == ["/a/rt/de23411d9e49", "/b/rt/de23411d9e49"]
    assert E.rt_candidates("/b/rt/de23411d9e49", roots=("/a/rt", "/b/rt")) == ["/b/rt/de23411d9e49", "/a/rt/de23411d9e49"]


@pytest.mark.parametrize("bad, why", [
    ("OT_PLAN_GATE_PRE=warn\n", "OT_EVENT"),
    ("OT_EVENT=x\nOT_EVENT=y\n", "twice"),
    ("OT_EVENT=x\nlower=1\n", "KEY=VALUE"),
    ("OT_EVENT=x\nA=$HOME\n", "literal"),
    ("OT_EVENT=x\nOT_RUN_PREFLIGHT=sometimes\n", "OT_RUN_PREFLIGHT"),
    ("OT_EVENT=x\nOT_EVENT_RT=current\n", "OT_EVENT_RT"),
    ("OT_EVENT=x\nOT_EVENT_INPUTS=rel/dir\n", "absolute"),
    ("OT_EVENT=x\nOT_EVENT_RT=aaaa11112222\nOT_TOOLSTALE_RT=/r/rt/bbbb33334444\n", "different"),
])
def test_parse_refuses_bad_files(bad, why):
    with pytest.raises(E.EventEnvError, match=why):
        E.parse(bad)


def test_lk_es0_gate_skip_is_a_conflict():
    ev = E.parse(GOOD)
    cmd = ["bash", "-c", "export OT_PLAN_GATE_SKIP=ANCHORDRY OT_PLAN_GATE_PRE=refuse; python3 bind.py"]
    c = E.gate_conflicts(ev, E.guarded_sets(" ".join(cmd)), "the command")
    assert any("OT_PLAN_GATE_SKIP=ANCHORDRY" in x and "does not set" in x for x in c)
    assert any("OT_PLAN_GATE_PRE=refuse" in x and "has OT_PLAN_GATE_PRE=warn" in x for x in c)
    # the same value as the event, and a value from a variable, are not findings
    assert E.gate_conflicts(ev, E.guarded_sets("OT_PLAN_GATE_PRE=warn OT_PLAN_GATE_SKIP=${SKIP:-}"), "x") == []
    assert E.gate_conflicts(ev, [("OT_TOOLSTALE_RT", "/r/rt/ffff00001111")], "x")
    assert E.caller_conflicts(ev, {"OT_PLAN_GATE_SKIP": "RELAYSINK", "HOME": "/h"})


def test_preflight_drops_host_without_inputs_and_reads_scripts(tmp_path):
    ev = E.parse(GOOD)
    have = set(E.probe_paths(ev))
    script = "/srv/opentallas-scratch2/claude/lane/bind_only.sh"

    def probe(h, paths, scripts):
        assert script in scripts
        rows = {p: (h == "epyc10" or not p.endswith("/tree")) and p in have for p in paths}
        rows["#answered"] = h != "epyc4"
        rows["#grep:" + script] = "OT_PLAN_GATE_PRE=warn" if h != "epyc9" else "OT_PLAN_GATE_SKIP=ANCHORDRY"
        return rows
    kept, per, glob = E.preflight(ev, ["epyc8", "epyc9", "epyc10", "epyc4"], ["bash", script], probe=probe, environ={})
    assert kept == ["epyc10", "epyc4"]                  # epyc4 did not answer: proves nothing, kept
    assert "event input /srv/opentallas-scratch2/claude/s81-j9/tree is missing" in per["epyc8"]
    assert any("script " + script in x and "OT_PLAN_GATE_SKIP" in x for x in per["epyc9"])
    assert glob == []


def test_probe_shell_roundtrip(tmp_path):
    a = tmp_path / "a"
    a.mkdir()
    sc = tmp_path / "s.sh"
    sc.write_text("export OT_PLAN_GATE_PRE=refuse OT_X=1\nOT_PLAN_GATE_SKIP=ANCHORDRY python3 x.py\n")
    paths = [str(a), str(tmp_path / "none")]
    r = subprocess.run(["bash", "-c", E.probe_sh(paths, [str(sc)])], capture_output=True, text=True)
    row = E.parse_probe(r.stdout, paths, [str(sc)])
    assert row[str(a)] is True and row[str(tmp_path / "none")] is False and row["#answered"]
    assert E.guarded_sets(row["#grep:" + str(sc)]) == [("OT_PLAN_GATE_PRE", "refuse"), ("OT_PLAN_GATE_SKIP", "ANCHORDRY")]


def test_cmd_scripts_finds_absolute_relative_and_bash_c():
    assert E.cmd_scripts(["bash", "/srv/x/claude/l/a.sh"]) == ["/srv/x/claude/l/a.sh"]
    assert E.cmd_scripts(["python3", "-I", "b.py"], d="/srv/x/claude/l") == ["/srv/x/claude/l/b.py"]
    assert E.cmd_scripts(["bash", "-c", "cd /x; bash /srv/x/claude/l/c.sh; echo"]) == ["/srv/x/claude/l/c.sh"]


def test_rt_pin_fragment_resolves_the_event_sha(tmp_path):
    (tmp_path / "r2" / "aaaa11112222" / "tools").mkdir(parents=True)
    ev = E.parse("OT_EVENT=x\nOT_EVENT_RT=aaaa11112222\n")
    frag = E.rt_pin_sh("T1", ev, roots=(str(tmp_path / "r1"), str(tmp_path / "r2")))
    r = subprocess.run(["bash", "-c", frag + 'echo "PIN=$OT_TOOLSTALE_RT"'], capture_output=True, text=True, env={"PATH": os.environ["PATH"]})
    assert f"PIN={tmp_path}/r2/aaaa11112222" in r.stdout
    assert f"OT_RUN_RTPIN T1 {tmp_path}/r2/aaaa11112222 event" in r.stderr
    frag = E.rt_pin_sh("T2", E.parse("OT_EVENT=x\nOT_EVENT_RT=bbbb33334444\n"), roots=(str(tmp_path / "r2"),))
    r = subprocess.run(["bash", "-c", frag + "true"], capture_output=True, text=True)
    assert r.returncode == 0 and "OT_RUN_RTPIN_EVENT_MISSING T2 bbbb33334444" in r.stderr


def test_check_cli(tmp_path, capsys):
    f = tmp_path / "S81-J9.env"
    f.write_text(GOOD)
    assert E.main(["--check", str(f)]) == 0
    assert "event S81-J9  rt de23411d9e49  preflight fail" in capsys.readouterr().out
    f.write_text("OT_EVENT=x\nOT_EVENT=y\n")
    assert E.main(["--check", str(f)]) == 1


# ---- ot-run integration ----

def test_ot_run_event_preflight_modes(tmp_path, monkeypatch):
    m = load_run()
    ev = E.parse(GOOD)
    calls = []
    monkeypatch.setattr(m, "not_run", lambda r, code=78: (_ for _ in ()).throw(SystemExit("NOT-RUN " + r)))
    monkeypatch.delenv("OT_RUN_PREFLIGHT", raising=False)

    def probe(h, paths, scripts):
        calls.append(h)
        return dict({p: h == "epyc10" for p in paths}, **{"#answered": True})
    say = []
    assert m.event_preflight(ev, ["epyc8", "epyc10"], ["true"], None, probe=probe, environ={}, say=say.append) == ["epyc10"]
    with pytest.raises(SystemExit, match="NOT-RUN PREFLIGHT .*no candidate host passes .*epyc8"):
        m.event_preflight(ev, ["epyc8"], ["true"], None, probe=probe, environ={}, say=say.append)
    with pytest.raises(SystemExit, match="NOT-RUN PREFLIGHT .*OT_PLAN_GATE_SKIP"):
        m.event_preflight(ev, ["epyc10"], ["env", "OT_PLAN_GATE_SKIP=ANCHORDRY", "true"], None, probe=probe, environ={}, say=say.append)
    # warn mode: findings are reported and every host stays
    monkeypatch.setenv("OT_RUN_PREFLIGHT", "warn")
    say.clear()
    assert m.event_preflight(ev, ["epyc8"], ["env", "OT_PLAN_GATE_SKIP=X", "true"], None, probe=probe, environ={}, say=say.append) == ["epyc8"]
    assert say and all(s.startswith("ot-run: PREFLIGHT WARN: ") for s in say)


def test_ot_run_remote_carries_event_env_and_pin(monkeypatch):
    m = load_run()
    m.EVENT[:] = [E.parse(GOOD)]
    seen = {}

    class P:
        def __init__(self, argv, **kw):
            seen["remote"] = argv[-1]
            self.stderr = iter([])

        def wait(self):
            return 255

        def kill(self):
            pass
    monkeypatch.setattr(m.subprocess, "Popen", P)
    monkeypatch.setattr(m, "_OTS", None)
    m.run("h", 1, ["true"], quiet=True)
    r = seen["remote"]
    heavy = r.index("/usr/local/bin/ot-heavy")
    assert r.index("OT_PLAN_GATE_PRE=warn ") < heavy and r.index("OT_EVENT=S81-J9 ") < heavy and r.index("OT_PGCAP=1 ") < heavy
    assert "/de23411d9e49" in r[:heavy] and "OT_RUN_RTPIN" in r[:heavy] and " event" in r[:heavy]
    assert "OT_EVENT_INPUTS" not in r


def test_hosts_with_needs_reports_paths_on_no_host():
    m = load_run()
    rows = {"epyc8": {"/": True, "/srv/a/claude/l/in.json": True, "/srv/a/claude/l/gone.json": False},
            "epyc9": {"/": True, "/srv/a/claude/l/in.json": False, "/srv/a/claude/l/gone.json": False}}
    nowhere = []
    kept, miss = m.hosts_with_needs(["epyc8", "epyc9"], [], ["/srv/a/claude/l/in.json", "/srv/a/claude/l/gone.json"],
                                    probe=lambda h, ps: {p: rows[h].get(p, False) for p in ps}, nowhere=nowhere)
    assert kept == ["epyc8"] and nowhere == ["/srv/a/claude/l/gone.json"]       # report only: the kept hosts are unchanged by it
    nowhere = []
    m.hosts_with_needs(["epyc9"], [], ["/srv/a/claude/l/gone.json"], probe=lambda h, ps: {p: False for p in ps}, nowhere=nowhere)
    assert nowhere == []                                                        # no host answered: nothing is reported


def test_deathclass_ignores_rt_pin_info_line():
    t = ("ot-run: -> epyc9\not-run: rt pinned for this unit: OT_TOOLSTALE_RT=/srv/opentallas-scratch2/claude/rt/de23411d9e49 "
         "(current; TOOLSTALE reference for the whole run)\not-heavy: admitted on renewed-glider as oth-u-1-2 after 1 s\n"
         "ot-run: RAN on epyc9 (unit oth-u-1-2): exit 1\n")
    cls, cause = D.classify(1, "bash x.sh", t, 3)
    assert cls == "NO-PATTERN" and "TOOLSTALE" not in cause and "only ot-run lines" in cause
    cls, cause = D.classify(1, "bash x.sh", t + "reset_tree.ResetError: declared parent svc_8/0\n", 30)
    assert "ResetError" in cause
