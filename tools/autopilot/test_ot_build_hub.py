"""ot-build hub side with a fake fleet: host choice, bind only when stale, kit stamped per type, precise refusals."""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ot_build_hub as H  # noqa: E402

SRC = "/srv/s/kw/src_kv"
CFG = {"dies": {"kv": {"src": SRC, "plan": SRC + "/p/plan.json", "gen_hosts": ["h1", "h2", "h3"], "gen_host": "h1",
                       "kit_rtl": {"mode": "bind", "asbuilt": SRC + "/p/ab.json", "bind_out": SRC + "_bind"},
                       "bind_env": {"OT_HCPARAM_ALL": "1"}, "die_gen_env": {"OT_KV_HEAD_KST": "2", "OT_VIEW": SRC + "/p/v.json"}},
                "head": {"src": "/x", "plan": "/x/p.json", "kit_rtl": {"mode": "script"}}}}


class Fleet:
    def __init__(self, tmp):
        self.tmp = tmp
        self.load = {"h1": (190.0, 96, True), "h2": (40.0, 96, True), "h3": (5.0, 96, False)}
        self.disk = {}
        self.stale = True
        self.types = {"ta": dict(block="b1", module="m_ta", rtl="r1")}
        self.calls = []
        self.verdict = "SIGNED"
        self.eff_asbuilt = SRC + "/p/ab.json"
        self.eff_tree = None
        self.eff_plan = SRC + "/p/plan.json"

    def eff(self, rc):
        extra = {"tree": self.eff_tree} if self.eff_tree else {}
        return "OT-BUILD EFFECTIVE " + json.dumps(dict(out="/srv/out/b_1", rc=rc, plan=self.eff_plan, asbuilt=self.eff_asbuilt, **extra,
                                                       keys={"bind": "k" * 64}, types=self.types, plan_rest="pr", asbuilt_sha="as",
                                                       tree_id="seal:1")) + "\n"

    def run(self, cmd, timeout=None, stdin=None):
        s = " ".join(cmd)
        if stdin is not None:                               # host probe
            h = next(x for x in cmd if x in self.load)
            ld, n, tree = self.load[h]
            return 0, f"L {ld} {ld}\nN {n}\nM 400\nT {int(tree)}\nD {self.disk.get(h, 900)}\nF 1\n", ""
        if "--status" in s:
            self.calls.append("status@" + next((x for x in cmd if x in self.load), "local"))
            return (3 if self.stale else 0), "ot-build: bind       STALE   input plan changed\n" + self.eff(3 if self.stale else 0), ""
        self.calls.append("write-script")
        return 0, "", ""

    def stream(self, cmd, env):
        s = " ".join(cmd)
        if "/ot-run" in s:
            self.calls.append("ot-run@" + cmd[cmd.index("--hosts") + 1])
            self.stale = False
            return 0, self.eff(0)
        if "private-spec" in cmd:
            self.calls.append("private-spec")
            self.spec = Path(cmd[cmd.index("--out") + 1]) / "spec.json"
            self.spec.parent.mkdir(parents=True, exist_ok=True)
            self.spec.write_text("{}")
            self.spec_cmd = cmd
            return 0, "private-spec kv/ta: spec\n"
        if "run-item" in cmd:
            self.calls.append("run-item")
            self.spec.with_name("result.json").write_text(json.dumps(dict(verdict=self.verdict, stage="signoff", kit="/k/ta",
                                                                          signoff={"path": "/k/ta/signoff.json"}, chain_reason="TT setup -80")))
            return 0, ""
        if "auto_export.py" in s:
            self.calls.append("export")
            return 0, ""
        raise AssertionError(s)


@pytest.fixture
def fleet(tmp_path, monkeypatch):
    rt = tmp_path / "rt" / "aaaabbbbcccc"
    (rt / "tools" / "autopilot").mkdir(parents=True)
    (rt / "tools" / "autopilot" / "ot_build.py").write_text("")
    (tmp_path / "rt" / "current").symlink_to(rt)
    monkeypatch.setattr(H, "RT_ROOT", tmp_path / "rt")
    monkeypatch.setattr(H, "AP_DIR", tmp_path / "ap")
    monkeypatch.setattr(H, "AUTO_BIND_GRACE_S", 0)
    monkeypatch.setenv("OT_BUILD_FORCE_SSH", "1")
    monkeypatch.setenv("OT_BUILD_HASH_CACHE", "off")
    monkeypatch.delenv("OT_LANE", raising=False)
    return Fleet(tmp_path)


def go(f, *argv):
    return H.main(["kv", "ta", "--lane", "L1"] + list(argv), run=f.run, stream=f.stream, cfg=CFG)


def test_end_to_end_then_everything_fresh(fleet, capsys):
    assert go(fleet) == 0
    assert fleet.calls == ["status@h2", "write-script", "ot-run@h2", "private-spec", "run-item", "export"]
    out = capsys.readouterr().out
    assert "bind host h2 = least loaded holder of the tree" in out and "h3" in out and "no tree" in out
    c = fleet.spec_cmd
    assert c[c.index("--bind-out") + 1] == "/srv/out/b_1" and c[c.index("--tree") + 1] == SRC and c[c.index("--goal") + 1] == "finish"
    assert "OT_HCPARAM_ALL" in out and "OT_KV_HEAD_KST" in out
    del fleet.calls[:]
    assert go(fleet) == 0
    assert fleet.calls == ["status@h2"]                    # bind fresh, kit fresh, export fresh


def test_other_types_row_change_rebinds_but_keeps_this_kit(fleet):
    assert go(fleet) == 0
    del fleet.calls[:]
    fleet.stale = True                                     # another type's row changed: the die re-binds ...
    assert go(fleet) == 0
    assert fleet.calls == ["status@h2", "write-script", "ot-run@h2"]      # ... this type's block and bound RTL did not move: no kit
    del fleet.calls[:]
    fleet.stale = True
    fleet.types = {"ta": dict(block="b1", module="m_ta", rtl="r2")}       # its bound RTL moved (a neighbour's depth): rebuild
    assert go(fleet) == 0
    assert fleet.calls[-3:] == ["private-spec", "run-item", "export"]


def test_forked_plan_probes_and_passes_live_remap_base(fleet):
    (H.RT_ROOT / "current/tools/autopilot/ot_build.py").write_text("--remap-base")
    commands = []

    def run(cmd, timeout=None, stdin=None):
        commands.append(cmd)
        return fleet.run(cmd, timeout=timeout, stdin=stdin)

    fork_plan = SRC + "/p/candidate.json"
    assert H.main(["kv", "ta", "--lane", "L1", "--plan", fork_plan, "--dry"],
                  run=run, stream=fleet.stream, cfg=CFG) == 3
    live_plan = CFG["dies"]["kv"]["plan"]
    assert any(fork_plan in " ".join(c) and live_plan in " ".join(c) and "--status" not in " ".join(c) for c in commands)
    assert any(f"--remap-base {live_plan}" in " ".join(c) and "--status" in " ".join(c) for c in commands)


def test_dry_reports_and_runs_nothing(fleet, capsys):
    assert go(fleet, "--dry") == 3
    assert fleet.calls == ["status@h2"] and "DRY" in capsys.readouterr().out
    fleet.stale = False
    assert go(fleet, "--dry") == 3                         # kit stale
    assert fleet.calls == ["status@h2", "status@h2"]


def test_not_signed_is_a_failure_and_reruns(fleet, capsys):
    fleet.verdict = "FAIL"
    assert go(fleet) == 1
    out = capsys.readouterr().out
    assert "verdict FAIL at stage signoff (want SIGNED)" in out and "TT setup -80" in out and "export" not in fleet.calls
    fleet.verdict = "SIGNED"
    del fleet.calls[:]
    assert go(fleet) == 0 and fleet.calls == ["status@h2", "private-spec", "run-item", "export"]


def test_refusals(fleet, capsys):
    assert H.main(["nodie", "ta", "--lane", "L1"], run=fleet.run, stream=fleet.stream, cfg=CFG) == 1
    assert "is not in the wave config" in capsys.readouterr().out
    assert H.main(["head", "ta", "--lane", "L1"], run=fleet.run, stream=fleet.stream, cfg=CFG) == 1
    assert "kit_rtl.mode is 'script'" in capsys.readouterr().out
    assert H.main(["kv", "tz", "--lane", "L1", "--goal", "bind"], run=fleet.run, stream=fleet.stream, cfg=CFG) == 1
    assert "type 'tz' is not a partition type" in capsys.readouterr().out
    for h in fleet.load:
        fleet.load[h] = (1.0, 96, False)
    assert go(fleet) == 1
    assert "no host holds the tree" in capsys.readouterr().out
    assert H.main(["kv", "ta"], run=fleet.run, stream=fleet.stream, cfg=CFG) == 2         # no --lane and no OT_LANE


def test_sealed_tree_with_tables_refreshed_outside_refuses_the_kit(fleet, capsys):
    fleet.eff_asbuilt = "/srv/out/b_1/.ot-build/plan/ab.json"
    assert go(fleet) == 1
    assert "refreshed R8 tables OUTSIDE the tree" in capsys.readouterr().out and "private-spec" not in fleet.calls
    assert go(fleet, "--goal", "bind") == 0


def test_bind_host_alias_path_of_the_tree_is_the_tree(fleet):
    alias = "/srv/s3/kw/src_kv"                               # epyc2 reaches the tree through scratch2 -> scratch3
    fleet.eff_tree, fleet.eff_asbuilt, fleet.eff_plan = alias, alias + "/p/ab.json", alias + "/p/plan.json"
    assert go(fleet) == 0 and "private-spec" in fleet.calls
    c = fleet.spec_cmd
    assert c[c.index("--plan") + 1] == SRC + "/p/plan.json" and c[c.index("--tree") + 1] == SRC


def test_tree_and_plan_override(fleet):
    r = H.resolve(CFG, "kv", tree="/srv/fork/t1")
    assert r["plan"] == "/srv/fork/t1/p/plan.json" and r["asbuilt"] == "/srv/fork/t1/p/ab.json"
    r = H.resolve(CFG, "kv", plan="/srv/delta/plan.json")
    assert r["tree"] == SRC and r["plan"] == "/srv/delta/plan.json" and r["asbuilt"] == SRC + "/p/ab.json"
    assert r["env"] == {"OT_HCPARAM_ALL": "1", "OT_KV_HEAD_KST": "2", "OT_VIEW": SRC + "/p/v.json"}
    assert H.resolve(CFG, "kv", tree="/srv/fork/t1")["env"]["OT_VIEW"] == "/srv/fork/t1/p/v.json"


class P:
    pid = 4242


def test_wave_rebind_states(fleet, tmp_path):
    st, alive, started = {}, {"v": True}, []

    def popen(cmd, **kw):
        started.append(cmd)
        kw["stdout"].write("ot-build: bind       BUILT   k in 600 s\n" + fleet.eff(0))
        return P()

    def rb(now):
        return H.wave_rebind(CFG, "kv", st, now=now, run=fleet.run, popen=popen, alive=lambda pid: alive["v"])
    r = rb(1000)
    assert r["state"] == "STARTED" and r["host"] == "h2" and len(started) == 1 and "input plan changed" in r["why"]
    assert "--plan-job" in started[0] and started[0][started[0].index("--hosts") + 1] == "h2"
    assert rb(1060)["state"] == "RUNNING" and len(started) == 1            # never a second bind of the same inputs
    alive["v"] = False
    fleet.stale = False
    r = rb(1120)
    assert r["state"] == "FRESH" and r["out"] == "/srv/out/b_1"
    n = len(fleet.calls)
    assert rb(1200)["state"] == "FRESH" and len(fleet.calls) == n          # within the TTL: no probe at all
    assert rb(1120 + H.WAVE_STATUS_TTL_S + 1)["state"] == "FRESH" and len(fleet.calls) == n + 1
    cfg2 = json.loads(json.dumps(CFG))
    cfg2["dies"]["kv"]["plan"] = SRC + "/p/plan2.json"                     # a new plan of record: the old verdict is void
    fleet.stale = True
    assert H.wave_rebind(cfg2, "kv", st, now=3000, run=fleet.run, popen=popen, alive=lambda pid: True)["state"] == "STARTED"


def test_wave_rebind_one_at_a_time_per_die_and_alias_paths(fleet):
    st, alive, started = {}, {"v": True}, []

    def popen(cmd, **kw):
        started.append(cmd)
        kw["stdout"].write(fleet.eff(0))
        return P()
    assert H.wave_rebind(CFG, "kv", st, now=10, run=fleet.run, popen=popen, alive=lambda pid: alive["v"])["state"] == "STARTED"
    cfg2 = json.loads(json.dumps(CFG))
    cfg2["dies"]["kv"]["plan"] = SRC + "/p/plan2.json"                     # inputs move while the first rebind runs
    r = H.wave_rebind(cfg2, "kv", st, now=20, run=fleet.run, popen=popen, alive=lambda pid: alive["v"])
    assert r["state"] == "RUNNING" and len(started) == 1 and "cap 1 per die" in r["why"]
    alive["v"] = False
    assert H.wave_rebind(cfg2, "kv", st, now=30, run=fleet.run, popen=popen, alive=lambda pid: alive["v"])["state"] == "STARTED"
    assert len(started) == 2                                               # the old verdict was dropped, the new inputs rebind
    st2 = {}
    fleet.stale = False
    fleet.eff_tree, fleet.eff_asbuilt = "/srv/s3/kw/src_kv", "/srv/s3/kw/src_kv/p/ab.json"
    r = H.wave_rebind(CFG, "kv", st2, now=40, run=fleet.run, popen=popen, alive=lambda pid: False)
    assert r["state"] == "FRESH" and r["asbuilt"] == SRC + "/p/ab.json"


def test_wave_rebind_waits_the_grace_and_uses_the_die_tools_pin(fleet, tmp_path, monkeypatch):
    monkeypatch.setattr(H, "AUTO_BIND_GRACE_S", 3600)
    pin = tmp_path / "rt" / "404887a342b0"
    (pin / "tools" / "die_plan").mkdir(parents=True)
    (pin / "tools" / "die_plan" / "bind.py").write_text("")
    cfg = json.loads(json.dumps(CFG))
    cfg["dies"]["kv"]["tools_sha"] = "404887a342b0ffff"
    st, started = {}, []

    def popen(cmd, **kw):
        started.append(cmd)
        return P()
    r = H.wave_rebind(cfg, "kv", st, now=1000, run=fleet.run, popen=popen, alive=lambda pid: True)
    assert r["state"] == "WAITING" and not started and "plan lane" in r["why"]
    n = len(fleet.calls)
    assert H.wave_rebind(cfg, "kv", st, now=2000, run=fleet.run, popen=popen, alive=lambda pid: True)["state"] == "WAITING"
    assert len(fleet.calls) == n                                           # no probe inside the grace
    fleet.stale = False                                                    # the plan lane's own bind made it fresh meanwhile
    assert H.wave_rebind(cfg, "kv", st, now=4700, run=fleet.run, popen=popen, alive=lambda pid: True)["state"] == "FRESH"
    assert not started
    st2 = {}
    fleet.stale = True
    H.wave_rebind(cfg, "kv", st2, now=1000, run=fleet.run, popen=popen, alive=lambda pid: True)
    r = H.wave_rebind(cfg, "kv", st2, now=4700, run=fleet.run, popen=popen, alive=lambda pid: True)
    assert r["state"] == "STARTED" and len(started) == 1 and "/rt/404887a342b0/" in " ".join(started[0])
    assert H.die_rt(CFG, "kv") is None


def test_wave_rebind_failure_is_reported_and_backs_off(fleet):
    st = {}

    def popen(cmd, **kw):
        kw["stdout"].write("ot-build: bind       FAILED  strict bind reports 3 error(s)\n" + fleet.eff(1))
        return P()
    assert H.wave_rebind(CFG, "kv", st, now=10, run=fleet.run, popen=popen, alive=lambda pid: False)["state"] == "STARTED"
    r = H.wave_rebind(CFG, "kv", st, now=20, run=fleet.run, popen=popen, alive=lambda pid: False)
    assert r["state"] == "FAILED" and "strict bind reports 3 error(s)" in r["why"]
    n = len(fleet.calls)
    assert H.wave_rebind(CFG, "kv", st, now=30, run=fleet.run, popen=popen, alive=lambda pid: False)["state"] == "FAILED"
    assert len(fleet.calls) == n
    assert H.wave_rebind(CFG, "head", st, now=30, run=fleet.run)["state"] == "FAILED"


def test_draining_host_is_not_picked(fleet, capsys):
    fleet.disk = {"h2": 180}                               # the least loaded holder is under its disk admit cap
    assert go(fleet, "--goal", "bind") == 0
    assert fleet.calls[0] == "status@h1"
    assert "disk 180 GB < 250 (draining)" in capsys.readouterr().out
