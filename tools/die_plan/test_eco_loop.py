"""KW-ECO-1: loop control of tools/die_plan/eco_loop.py (late-stage ECO on a routed DB) with a fake runner (no
OpenROAD): eligibility, stop rules (PASS / no improvement / max iterations / error), best pick + pruning, record."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import eco_loop as E  # noqa: E402


@pytest.mark.parametrize("failure", ["flexpa", "grt_hang", "stage_mismatch"])
def test_strict_one_pass_disables_each_recovery_dispatch(tmp_path, monkeypatch, failure):
    import threading
    stopped = threading.Event()
    monkeypatch.setattr(E, "GRT_FLAT_S", 5)
    monkeypatch.setattr(E, "WATCH_POLL_S", 0.01)
    monkeypatch.setattr(E, "stop_eco_container", lambda pd: (stopped.set() or ["fixture-own-pass"]))
    fake = {"flexpa": lambda: Sig11([rec(5, 5)]),
            "grt_hang": lambda: Hang([rec(5, 5)], stopped),
            "stage_mismatch": lambda: Stale([rec(5, 5)])}[failure]()
    k = kit(tmp_path)
    result = E.run_loop(k, base_rec(k, rec(-20, 2)), tmp_path / "eco", run=fake,
                        strict_one_pass=True, keep=True)
    runs = [cmd for cmd, _ in fake.calls if cmd[0] == "bash" and cmd[1].endswith("prd_run.sh")]
    assert len(runs) == 1
    assert len(result["iterations"]) == 1 and result["verdict"] != "PASS"
    assert result["physical_dispatch_budget"] == dict(limit=1, dispatched=1, blocked=[])
    assert not any(key in result for key in ("repair_rc_retry", "grt_hang_retry", "stage_retry"))
    assert json.loads((Path(result["root"]) / "eco_loop.json").read_text())["strict_one_pass"] is True


def test_strict_one_pass_budget_blocks_split_mode_second_physical_call(tmp_path, monkeypatch):
    k = kit(tmp_path, mm=False)
    monkeypatch.setattr(E, "passes", lambda *a: ["t0", "b0"])
    fake = Fake([rec(5, 5)])
    result = E.run_loop(k, base_rec(k, rec(-5, -2)), tmp_path / "eco", run=fake,
                        strict_one_pass=True, keep=True)
    runs = [cmd for cmd, _ in fake.calls if cmd[0] == "bash" and cmd[1].endswith("prd_run.sh")]
    assert len(runs) == 1 and result["verdict"] != "PASS"
    assert result["physical_dispatch_budget"]["dispatched"] == 1
    assert len(result["physical_dispatch_budget"]["blocked"]) == 1


def test_strict_one_pass_cli_is_opt_in(tmp_path, monkeypatch):
    seen = []
    def capture(*args, **kwargs):
        seen.append(kwargs["strict_one_pass"])
        return dict(verdict="ERROR", reason="fixture", root=str(tmp_path))
    monkeypatch.setattr(E, "run_loop", capture)
    monkeypatch.setattr(E, "summary", lambda r: "fixture")
    for extra, expected in (([], False), (["--strict-one-pass"], True)):
        monkeypatch.setattr(sys, "argv", ["eco_loop.py", "run", "--kit", str(tmp_path),
                                          "--signoff", str(tmp_path / "signoff.json")] + extra)
        assert E.main() != 0
        assert seen[-1] is expected


def test_stage_so_keeps_selected_tool_cohort_and_kit_hooks(tmp_path):
    k = tmp_path / "old_kit"
    k.mkdir()
    # The observed failure: a refreshed signoff alongside a legacy helper.
    (k / "signoff.py").write_bytes((E.HERE / "signoff.py").read_bytes())
    (k / "sdc_lint.py").write_text("# old helper, no policy_uncertainty API\n")
    (k / "lec.py").write_text("# old shared Python tool\n")
    (k / "clock_family.tcl").write_text("# old signoff helper\n")
    local = {"kit_only.py": "# custom kit input helper\n",
             "cts_post.tcl": "# kit-specific clock geometry\n",
             "run_kit.sh": "# kit-specific runner\n"}
    for name, text in local.items():
        (k / name).write_text(text)
    dp = E.stage_so(k, tmp_path / "eco") / "tools" / "die_plan"
    for name in ("signoff.py", "sdc_lint.py", "lec.py"):
        assert (dp / name).read_bytes() == (E.HERE / name).read_bytes()
    for name, text in local.items():
        assert (dp / name).read_text() == text
    assert (dp / "clock_family.tcl").read_text() != "# old signoff helper\n"
    # Exercise the staged entry point; the mixed helper formerly raised before
    # `bundle` could run, without requiring an OpenROAD vehicle.
    result = subprocess.run([sys.executable, "-I", str(dp / "signoff.py"), "bundle",
                             str(tmp_path / "pass_bundle")], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "SIGNOFF_BUNDLE" in result.stdout
    assert (k / "sdc_lint.py").read_text() == "# old helper, no policy_uncertainty API\n"


@pytest.mark.parametrize("relative", ["eco2/i1", "repairs/custom/i1", None])
def test_prd_staging_preserves_inputs_without_copying_own_output(tmp_path, relative):
    k = tmp_path / "kit"
    base = k / "run/results/asap7/dp_x/base"
    base.mkdir(parents=True)
    for name in ("5_1_grt.odb", "4_1_cts.odb", "6_final.spef"):
        (base / name).write_text("fixture\n")
    (k / "config.mk").write_text("export DESIGN_NAME = x\n")
    (k / "constraint.sdc").write_text("# original kit SDC\n")
    (k / "pins.json").write_text('{"kit_input": true}\n')
    out = k / relative if relative else tmp_path / "external_pass"
    so = E.stage_so(k, tmp_path / "selected_tools")
    env = dict(os.environ, OT_PRD_SEED_CHECK="0", OT_PRD_FROM="grt")
    result = subprocess.run(["bash", str(E.PRD / "prd_mk.sh"), str(k), str(out), "b0", str(so)],
                            env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (out / "pins.json").read_bytes() == (k / "pins.json").read_bytes()
    assert (out / "constraint.sdc").read_bytes() == (k / "constraint.sdc").read_bytes()
    if relative:
        assert not (out / Path(relative).parts[0]).exists()


def rec(tt=-5.0, ff=-3.0, slew=0, drc=0, verdict=None, local=None, extra_fail=None, base="/x/base"):
    checks = {"setup_tt": {"verdict": "PASS" if tt >= 0 else "FAIL", "wns_ps": tt},
              "hold_ff": {"verdict": "PASS" if ff >= 0 else "FAIL", "wns_ps": ff},
              "drv": {"verdict": "PASS" if not slew else "FAIL", "by_corner": {"tt": {"slew": slew, "cap": 0.0},
                                                                               "ff": {"slew": 0.0, "cap": 0.0}}},
              "drc": {"verdict": "PASS" if not drc else "FAIL", "count": drc},
              "clock": {"verdict": "PASS"}, "pg": {"verdict": "PASS"}}
    if extra_fail:
        checks[extra_fail] = {"verdict": "FAIL"}
    bad = any(v.get("verdict") == "FAIL" for v in checks.values())
    return {"verdict": verdict or ("NOT SIGNED" if bad else "SIGNED"), "local_verdict": local,
            "inputs": {"base": base, "odb": base + "/6_final.odb"}, "checks": checks}


def kit(tmp_path, mm=True):
    k = tmp_path / "kit"
    (k / "signoff").mkdir(parents=True)
    (k / "config.mk").write_text("export DESIGN_NAME = x\n" + ("override export OT_HOLD_MM = 1\n" if mm else ""))
    (k / "signoff.py").write_text("# kit sign-off\n")
    return k


class Fake:
    """plays prd_mk.sh / prd_run.sh / abstract / signoff.py; results[i] = sign-off record of iteration i+1 (None:
    prd_run fails)"""

    def __init__(self, results):
        self.results = list(results)
        self.calls = []
        self.n = 0          # sign-offs done = iterations finished

    def __call__(self, cmd, **kw):
        self.calls.append((cmd, kw.get("env") or {}))
        if cmd[0] == "bash" and cmd[1].endswith("prd_mk.sh"):
            d = Path(cmd[3])
            (d / "run/results/asap7/n/base").mkdir(parents=True)
            (d / "run/objects").mkdir(parents=True)
            (d / "config.mk").write_text("eco overrides\n")
            (d / "signoff.py").write_text("# kit sign-off\n")
            (d / "prd_hook.tcl").write_text((E.PRD / "prd_hook.tcl").read_text())
            return 0
        if cmd[0] == "bash" and cmd[1].endswith("prd_run.sh"):
            scope = (kw.get("env") or {}).get("OT_HOLD_REPAIR_SCOPE")
            if scope in E.HOLD_SCOPES:
                with (Path(cmd[2]) / "run_prd.log").open("a") as f:
                    f.write(f"OT_PRD_HOLD_SCOPE_VERIFIED scope={scope} entered=1 restored=1 completed=1\n")
            return 9 if self.results[self.n] is None else 0
        if "run" in cmd and "--out" in cmd:
            out = Path(cmd[cmd.index("--out") + 1])
            out.mkdir(parents=True)
            d = Path(cmd[cmd.index("--kit") + 1])
            r = self.results[self.n]
            self.n += 1
            r["inputs"] = {"base": str(d / "run/results/asap7/n/base")}
            (out / "signoff.json").write_text(json.dumps(r))
            return 0 if r["verdict"] == "SIGNED" else 1
        return 0


def base_rec(k, r):
    p = k / "signoff/signoff.json"
    p.write_text(json.dumps(r))
    return p


def test_eligibility_classes():
    assert E.eligible(rec(-12.5, -13.6, slew=72))[0]
    assert E.eligible(rec(10, -2, drc=3))[0]
    assert not E.eligible(rec(10, 5))[0]                                    # signed
    ok, why = E.eligible(rec(-1, 5, extra_fail="face_guard"))
    assert not ok and "face_guard" in why                                    # structural gate -> not an ECO
    ok, why = E.eligible(rec(-1, 5, drc=E.DRC_SMALL + 1))
    assert not ok and "ROUTING" in why
    assert not E.eligible({})[0]
    assert E.metrics(rec(5, 2, verdict="LOCAL_PASS_NEEDS_PARENT", local="SIGNED"))["signed"]


def test_stop_rules():
    p = E.metrics(rec(-10, -5, slew=10))
    assert E.improved(p, E.metrics(rec(-9, -5, slew=10)))                  # +1 ps
    assert not E.improved(p, E.metrics(rec(-9.5, -5, slew=10)))            # +0.5 ps, DRV flat
    assert E.improved(p, E.metrics(rec(-10, -5, slew=9)))                  # DRV falls
    assert not E.improved(p, E.metrics(rec(-10, -5, slew=11)))


@pytest.fixture
def three_iter(monkeypatch):
    """the iteration machinery stays testable; the live limit is test_one_iteration_is_the_limit"""
    monkeypatch.setattr(E, "MAX_ITER", 3)
    return dict(max_iter=3)


def test_one_iteration_is_the_limit(tmp_path, capsys, monkeypatch):
    assert E.MAX_ITER == 1
    k = kit(tmp_path)
    b = base_rec(k, rec(-12, -13))
    f = Fake([rec(-4, -6), rec(1, 2)])
    r = E.run_loop(k, b, run=f, mem=8, cpus=2)
    assert r["verdict"] == "EXHAUSTED" and len(r["iterations"]) == 1 and r["max_iter"] == 1 and "REDESIGN" in r["reason"]
    with pytest.raises(ValueError, match="refused"):
        E.run_loop(k, b, run=f, max_iter=2)
    monkeypatch.setattr(sys, "argv", ["eco_loop.py", "run", "--kit", str(k), "--max-iter", "2"])
    assert E.main() == 2
    assert "--max-iter 2 refused" in capsys.readouterr().err


def far(**kw):
    r = rec(**{k: v for k, v in kw.items() if k in ("tt", "ff", "slew", "drc")})
    for gate, n in (("setup_tt", "tt_n"), ("hold_ff", "ff_n")):
        r["checks"][gate]["violators"] = kw.get(n, 0)
    return r


@pytest.mark.parametrize("kw,near,word", [
    (dict(tt=-30, ff=-30, tt_n=100, ff_n=100, slew=0, drc=49), True, ""),
    (dict(tt=-30.1, ff=5), False, "setup WNS"),
    (dict(tt=5, ff=-31), False, "hold WNS"),
    (dict(tt=-5, ff=5, tt_n=101), False, "setup 101 endpoints"),
    (dict(tt=5, ff=-5, ff_n=101), False, "hold 101 endpoints"),
    (dict(tt=-5, ff=5, drc=50), False, "DRC 50"),
])
def test_near_miss_numbers(kw, near, word):
    ok, beyond, _ = E.near_miss(far(**kw))
    assert ok == near and (not word or word in "; ".join(beyond))


def test_large_miss_stops_before_any_pnr_unless_owner_override(tmp_path):
    k = kit(tmp_path)
    b = base_rec(k, far(tt=-45, ff=-3, tt_n=5, ff_n=500))
    f = Fake([rec(1, 2)])
    r = E.run_loop(k, b, run=f, mem=8, cpus=2)
    assert r["verdict"] == "NOT_NEAR_MISS" and not f.calls and not Path(r["root"]).exists()
    assert "setup WNS -45" in r["reason"] and "hold 500 endpoints" in r["reason"] and "not a near miss" in E.summary(r)
    r = E.run_loop(k, b, run=f, mem=8, cpus=2, owner_override=True)
    assert r["verdict"] == "PASS" and f.calls and r["near_miss"]["owner_override"]


def test_slew_counts_nets_and_pins_are_advisory(tmp_path, capsys):
    r = far(tt=-5, ff=5, slew=166)
    ok, beyond, warn = E.near_miss(r)
    assert ok and not beyond and "166 slew pins" in warn[0]
    r["checks"]["drv"]["by_corner"]["tt"]["slew_nets"] = 11
    assert E.near_miss(r)[0] and not E.near_miss(r)[2]
    r["checks"]["drv"]["by_corner"]["tt"]["slew_nets"] = 21
    assert "21 slew nets" in E.near_miss(r)[1][0]
    k = kit(tmp_path)
    assert E.run_loop(k, base_rec(k, far(tt=-5, ff=5, slew=166)), run=Fake([rec(1, 2)]), mem=8, cpus=2)["verdict"] == "PASS"
    assert "166 slew pins" in capsys.readouterr().out


def test_port_only_hold_does_not_count(tmp_path):
    k = kit(tmp_path)
    r = far(tt=5, ff=-120, ff_n=2000, slew=3)
    b = base_rec(k, r)
    assert not E.near_miss(r, b)[0]                                        # no FF census: a plain large hold miss
    (k / "signoff/ff").mkdir()
    census = dict(std_nviol_min=2000, std_min_start=dict(port=2000, other=0, reg=0, trunc=0, err=0, ports=["a"]))
    (k / "signoff/ff/corner.json").write_text(json.dumps(census))
    ok, beyond, warn = E.near_miss(r, b)
    assert ok and not beyond and "port-only" in warn[0]
    census["std_min_start"].update(other=1, port=1999)
    (k / "signoff/ff/corner.json").write_text(json.dumps(census))
    assert not E.near_miss(r, b)[0]
    r["checks"]["hold_ff"]["verdict"] = "PASS"                             # current record: local PASS, the parent's obligation
    assert E.near_miss(r, b)[0]


def test_pass_on_second_iteration(tmp_path, three_iter):
    k = kit(tmp_path)
    b = base_rec(k, rec(-12, -13, slew=72))
    f = Fake([rec(-4, -6, slew=10), rec(1, 2)])
    r = E.run_loop(k, b, run=f, mem=8, cpus=2, **three_iter)
    assert r["verdict"] == "PASS" and len(r["iterations"]) == 2
    assert r["best"]["n"] == 2 and Path(r["best"]["signoff"]).is_file()
    assert r["kind"] == "eco" and r["base_routed_db"] == "/x/base/6_final.odb" and r["flow"]["tools_sha256"]
    assert all(it["commands"] for it in r["iterations"])
    # iteration 2 starts from iteration 1's routed dir; the superseded iteration 1 run data is pruned, best kept
    mk2 = [c for c, _ in f.calls if c[0] == "bash" and c[1].endswith("prd_mk.sh")][1]
    assert mk2[2] == r["iterations"][0]["dir"] and mk2[4] == f"m{E.HOLD_MARGIN_PS}"
    assert not (Path(r["iterations"][0]["dir"]) / "run/results").exists()
    assert (Path(r["best"]["dir"]) / "run/results").exists()
    # sign-off on the kit's own config.mk (ECO overrides kept aside as config_eco.mk)
    d = Path(r["best"]["dir"])
    assert (d / "config.mk").read_text() == (k / "config.mk").read_text()
    assert (d / "config_eco.mk").read_text() == "eco overrides\n\noverride export OT_HOLD_REPAIR_SCOPE = reg2reg\n"
    assert json.loads((Path(r["root"]) / "eco_loop.json").read_text())["verdict"] == "PASS"
    # every ECO pass: route-keeping incremental DRT, finish only (the loop signs off itself)
    env = [e for c, e in f.calls if c[0] == "bash" and c[1].endswith("prd_run.sh")][0]
    assert env["OT_PRD_FROM"] == "route" and env["OT_PRD_POST"] == "0"


def test_no_improvement_stops_and_keeps_best(tmp_path, three_iter):
    k = kit(tmp_path, mm=False)
    b = base_rec(k, rec(10, -8, slew=40))
    f = Fake([rec(10, -3, slew=5), rec(10, -2.6, slew=6), rec(10, 1)])
    r = E.run_loop(k, b, run=f, mem=8, cpus=2, **three_iter)
    assert r["verdict"] == "EXHAUSTED" and len(r["iterations"]) == 2 and "no improvement" in r["reason"]
    assert r["best"]["n"] == 2                                                 # -2.6 is better than -3
    assert r["iterations"][0]["variant"] == f"t{E.HOLD_MARGIN_PS}+b{E.HOLD_MARGIN_PS}"                          # TT slew + FF hold: both passes
    s = E.summary(r)
    assert s.startswith("late-ECO exhausted (2 it") and "FF -8->-2.6" in s


def test_max_iterations(tmp_path, three_iter):
    k = kit(tmp_path)
    b = base_rec(k, rec(-30, -20))
    f = Fake([rec(-20, -20), rec(-10, -20), rec(-5, -20), rec(5, 5)])
    r = E.run_loop(k, b, run=f, mem=8, cpus=2, **three_iter)
    assert r["verdict"] == "EXHAUSTED" and len(r["iterations"]) == E.MAX_ITER and r["best"]["n"] == 3
    assert "3 iteration(s)" in r["reason"]


def test_error_iteration_and_drc_mode(tmp_path):
    k = kit(tmp_path)
    b = base_rec(k, rec(5, -3, drc=4))
    r = E.run_loop(k, b, run=Fake([None]), mem=8, cpus=2)
    assert r["verdict"] == "ERROR" and r["iterations"][0]["status"] == "ERROR" and "best" not in r
    assert r["iterations"][0]["mode"] == "grt"                                 # DRC > 0: full DRT from GRT


def test_not_eligible_writes_nothing(tmp_path):
    k = kit(tmp_path)
    b = base_rec(k, rec(-3, 5, extra_fail="sdc_lint"))
    f = Fake([])
    r = E.run_loop(k, b, run=f, mem=8, cpus=2)
    assert r["verdict"] == "NOT_ELIGIBLE" and not f.calls and not Path(r["root"]).exists()
    assert "not eligible" in E.summary(r)


def test_post_runner_used_when_kit_has_one(tmp_path):
    k = kit(tmp_path)
    b = base_rec(k, rec(-3, 5))
    calls = []

    def run(cmd, **kw):
        calls.append(cmd)
        if cmd[1].endswith("prd_mk.sh"):
            d = Path(cmd[3])
            (d / "run/results/asap7/n/base").mkdir(parents=True)
            (d / "config.mk").write_text("eco\n")
            (d / "prd_hook.tcl").write_text((E.PRD / "prd_hook.tcl").read_text())
            (d / "run_kit_hbm.sh").write_text('if [ "$GOAL" = post ]; then :; fi\n')
        elif cmd[1].endswith("prd_run.sh"):
            scope = (kw.get("env") or {}).get("OT_HOLD_REPAIR_SCOPE")
            if scope in E.HOLD_SCOPES:
                (Path(cmd[2]) / "run_prd.log").write_text(f"OT_PRD_HOLD_SCOPE_VERIFIED scope={scope} entered=1 restored=1 completed=1\n")
        elif cmd[1].endswith("run_kit_hbm.sh"):
            d = Path(cmd[2])
            (d / "signoff").mkdir()
            r = rec(2, 5)
            r["inputs"] = {"base": str(d / "run/results/asap7/n/base")}
            (d / "signoff/signoff.json").write_text(json.dumps(r))
        return 0
    r = E.run_loop(k, b, run=run, mem=8, cpus=2, runner=str(k / "run_kit_hbm.sh"))
    assert r["verdict"] == "PASS"
    post = [c for c in calls if c[1].endswith("run_kit_hbm.sh")][0]
    assert post[3] == "post" and not any("abstract" in " ".join(map(str, c)) for c in calls)


def _refusing_runner(d):
    """a kit runner carrying the real stage-resume refusal line of the generated RUN_KIT"""
    line = next(l for l in (E.HERE / "gen_phys.py").read_text().splitlines() if 'case "$GOAL" in floorplan|place' in l)
    assert "unsupported" in line and "post" not in line.split(")")[0]
    (d / "run_kit_hbm.sh").write_text('K=$(cd "$1" && pwd); GOAL=$2  # GOAL=post signs off\n'
                                      'if [ -f "$K/resume.json" ]; then\n' + line + '\nfi\n'
                                      'mkdir -p "$K/signoff"; echo "$OT_ALLOW_RESYNTH" > "$K/allow"; cp "$K/rec.json" "$K/signoff/signoff.json"\n')


def _resumed_post_run(k, calls):
    def run(cmd, **kw):
        calls.append((cmd, kw))
        if cmd[1].endswith("prd_mk.sh"):
            d = Path(cmd[3])
            (d / "run/results/asap7/n/base").mkdir(parents=True)
            (d / "config.mk").write_text("eco\n")
            (d / "prd_hook.tcl").write_text((E.PRD / "prd_hook.tcl").read_text())
            (d / "resume.json").write_text('{"start": "cts"}\n')
            _refusing_runner(d)
            r = rec(2, 5)
            r["inputs"] = {"base": str(d / "run/results/asap7/n/base")}
            (d / "rec.json").write_text(json.dumps(r))
        elif cmd[1].endswith("prd_run.sh"):
            scope = (kw.get("env") or {}).get("OT_HOLD_REPAIR_SCOPE")
            if scope in E.HOLD_SCOPES:
                (Path(cmd[2]) / "run_prd.log").write_text(f"OT_PRD_HOLD_SCOPE_VERIFIED scope={scope} entered=1 restored=1 completed=1\n")
        elif cmd[1].endswith("run_kit_hbm.sh"):
            return subprocess.call(["bash"] + cmd[1:], env=kw.get("env"), stdout=subprocess.DEVNULL)
        return 0
    return run


def test_post_runs_on_a_stage_resumed_kit(tmp_path):
    k = kit(tmp_path)
    (k / "resume.json").write_text('{"start": "cts"}\n')
    b = base_rec(k, rec(-3, 5))
    calls = []
    r = E.run_loop(k, b, run=_resumed_post_run(k, calls), mem=8, cpus=2, runner=str(k / "run_kit_hbm.sh"))
    assert r["verdict"] == "PASS"
    it = r["iterations"][0]
    d = Path(it["dir"])
    assert it["rc"]["signoff"] == 0 and it["stage_resume_set_aside"] == str(d / "resume.json.was_stage_resume")
    assert not (d / "resume.json").exists() and (d / "resume.json.was_stage_resume").is_file()
    assert not (d / "FAIL_PREFLOOR").exists()
    assert (d / "allow").read_text().strip() == "1"      # the runner's RESYNTH-GUARD stays skipped, as with resume.json
    assert (k / "resume.json").is_file()                 # only the pass dir changes


def test_post_keeps_refusal_when_resume_is_not_set_aside(tmp_path, monkeypatch):
    """control: the refusal is real, so the test above is proving the fix"""
    monkeypatch.setattr(E, "set_aside_stage_resume", lambda d: None)
    k = kit(tmp_path)
    b = base_rec(k, rec(-3, 5))
    calls = []
    r = E.run_loop(k, b, run=_resumed_post_run(k, calls), mem=8, cpus=2, runner=str(k / "run_kit_hbm.sh"))
    assert r["verdict"] != "PASS" and r["iterations"][0]["rc"]["signoff"] == 10


def test_post_without_resume_sets_no_override(tmp_path):
    k = kit(tmp_path)
    b = base_rec(k, rec(-3, 5))
    calls = []

    def run(cmd, **kw):
        calls.append((cmd, kw))
        if cmd[1].endswith("prd_mk.sh"):
            d = Path(cmd[3])
            (d / "run/results/asap7/n/base").mkdir(parents=True)
            (d / "config.mk").write_text("eco\n")
            (d / "prd_hook.tcl").write_text((E.PRD / "prd_hook.tcl").read_text())
            (d / "run_kit_hbm.sh").write_text('if [ "$GOAL" = post ]; then :; fi\n')
        elif cmd[1].endswith("prd_run.sh"):
            scope = (kw.get("env") or {}).get("OT_HOLD_REPAIR_SCOPE")
            if scope in E.HOLD_SCOPES:
                (Path(cmd[2]) / "run_prd.log").write_text(f"OT_PRD_HOLD_SCOPE_VERIFIED scope={scope} entered=1 restored=1 completed=1\n")
        elif cmd[1].endswith("run_kit_hbm.sh"):
            d = Path(cmd[2])
            (d / "signoff").mkdir()
            r = rec(2, 5)
            r["inputs"] = {"base": str(d / "run/results/asap7/n/base")}
            (d / "signoff/signoff.json").write_text(json.dumps(r))
        return 0
    r = E.run_loop(k, b, run=run, mem=8, cpus=2, runner=str(k / "run_kit_hbm.sh"))
    assert r["verdict"] == "PASS" and "stage_resume_set_aside" not in r["iterations"][0]
    assert "env" not in [kw for c, kw in calls if c[1].endswith("run_kit_hbm.sh")][0]


def test_single_mode_passes():
    m = lambda **k: dict(dict(tt=5, ff=5, drv_tt=0, drv_ff=0, drc=0), **k)  # noqa: E731
    k = Path("/nonexistent")
    assert E.passes(k, m(tt=-3), 10) == ["t10"]                               # TT setup only
    assert E.passes(k, m(drv_tt=4), 10) == ["t10"]                            # TT slew only
    assert E.passes(k, m(ff=-2), 10) == ["b10"]
    assert E.passes(k, m(tt=-1, drv_ff=3), 10) == ["t10", "b10"]
    assert E.passes(k, m(drc=3), 10) == ["b10"]
    assert E.passes(k, m(), 10) == ["b10"]
    assert E.metrics(rec(-1, 5, slew=7))["drv_tt"] == 7


def test_mm_kit_single_m_pass(tmp_path):
    k = kit(tmp_path)
    assert E.passes(k, dict(tt=-3, ff=-3, drv_tt=5, drv_ff=5, drc=0), 10) == ["m10"]


def test_t_then_b_chain(tmp_path):
    k = kit(tmp_path, mm=False)
    b = base_rec(k, rec(-6, -2, slew=0))
    f = Fake([rec(2, 3)])
    r = E.run_loop(k, b, run=f, mem=8, cpus=2)
    assert r["verdict"] == "PASS"
    it = r["iterations"][0]
    mk = [c for c, _ in f.calls if c[0] == "bash" and c[1].endswith("prd_mk.sh")]
    assert [c[4] for c in mk] == [f"t{E.HOLD_MARGIN_PS}", f"b{E.HOLD_MARGIN_PS}"]
    assert mk[0][3].endswith("/i1t") and mk[1][2] == mk[0][3] and mk[1][3] == it["dir"]
    envs = [e for c, e in f.calls if c[0] == "bash" and c[1].endswith("prd_run.sh")]
    assert envs[1]["OT_PRD_FROM"] == "route"
    # the b pass and the sign-off start from the kit's own config; the t pass dir is pruned, the final dir kept
    assert (Path(mk[0][3]) / "config.mk").read_text() == (k / "config.mk").read_text()
    assert not (Path(mk[0][3]) / "run/results").exists() and (Path(it["dir"]) / "run/results").exists()
    assert set(it["rc"]) >= {"prd_mk_t", "prd_run_t", "prd_mk_b", "prd_run_b", "signoff"}


def test_postroute_lec_uses_actual_capsule_and_fresh_receipt(tmp_path):
    k = kit(tmp_path)
    d = tmp_path / "eco"
    (d / "base").mkdir(parents=True)
    (d / "lec").mkdir()
    (d / "lec/lec.json").write_text(json.dumps({"verdict": "EQUIVALENT"}))
    res = {"root": str(d), "best": {"dir": str(d), "base": str(d / "base")}}
    calls = []
    def fail(cmd, **kw):
        calls.append(cmd)
        assert cmd[2] == str(d.resolve())
        out = Path(cmd[cmd.index("--out") + 1])
        assert out != d / "lec" and not (out / "lec.json").exists()
        return 1
    assert not E.run_lec(k, res, 8, 2, run=fail)
    assert res["lec"]["verdict"] is None and res["lec"]["exit"] == 1
    oldout = res["lec"]["record"]
    def passed(cmd, **kw):
        out = Path(cmd[cmd.index("--out") + 1])
        (out / "lec.json").write_text(json.dumps({"verdict": "EQUIVALENT"}))
        return 0
    assert E.run_lec(k, res, 8, 2, run=passed)
    assert res["lec"]["record"] != oldout
    assert json.loads((d / "lec/lec.json").read_text())["verdict"] == "EQUIVALENT"


class OomFake(Fake):
    """prd_run.sh killed by the docker memory cap (rc 137), as VEs autopilot 246986099dc1"""

    def __init__(self, rc=137, log=None):
        super().__init__([None])
        self.rc, self.log = rc, log

    def __call__(self, cmd, **kw):
        if cmd[0] == "bash" and cmd[1].endswith("prd_run.sh"):
            self.calls.append((cmd, kw.get("env") or {}))
            if self.log is not None:
                (Path(cmd[2]) / "run_prd.log").write_text(self.log)
            return self.rc
        return super().__call__(cmd, **kw)


def test_prd_run_rc137_is_eco_oom(tmp_path):
    k = kit(tmp_path)
    b = base_rec(k, rec(41.71, -9.29))
    r = E.run_loop(k, b, run=OomFake(137, log="make: *** [do-route] Error 137\n"), mem=24, cpus=2)
    it = r["iterations"][0]
    assert r["verdict"] == "ECO_OOM" and it["status"] == "ECO_OOM"
    assert "OOM-killed at 24 GB docker cap (rc 137)" in it["reason"]
    assert E.summary(r).startswith("late-ECO OOM")
    assert json.loads((Path(r["root"]) / "eco_loop.json").read_text())["verdict"] == "ECO_OOM"


def test_kill_text_is_eco_oom_and_other_rc_is_error(tmp_path):
    k = kit(tmp_path)
    b = base_rec(k, rec(5, -3))
    r = E.run_loop(k, b, run=OomFake(2, log="make: *** [do-route] Killed\n"), mem=8, cpus=2)
    assert r["verdict"] == "ECO_OOM"
    k2 = kit(tmp_path / "b")
    b2 = base_rec(k2, rec(5, -3))
    r2 = E.run_loop(k2, b2, run=OomFake(245, log="Signal 11 received\n"), mem=8, cpus=2)
    assert r2["verdict"] == "ERROR" and "route / clock-freeze check / finish failed" in r2["iterations"][0]["reason"]
    assert E.summary(r2).startswith("late-ECO exhausted")


def test_measured_peak_floors_eco_mem(tmp_path):
    k = kit(tmp_path)
    (k / "run_finish.fromcts.log").write_text("[INFO DRT-0267] cpu time = 1, memory = 21013.48 (MB), peak = 22301.00 (MB)\n")
    lg = k / "run/logs/asap7/n/base"
    lg.mkdir(parents=True)
    (lg / "3_3_place_gp.log").write_text("Elapsed time: 0:10. Peak memory: 1957844KB.\nMEM: 807.23 MB peak\n")
    assert E.measured_peak_gb(k) == pytest.approx(21.78, abs=0.01)
    assert E.eco_mem(k, 24) == (33, pytest.approx(21.78, abs=0.01))
    assert E.eco_mem(k, 64)[0] == 64                                          # never below the request
    assert E.eco_mem(kit(tmp_path / "e"), 24) == (24, 0.0)                    # no logs: request unchanged
    b = base_rec(k, rec(41.71, -9.29))
    f = OomFake(137, log="Killed\n")
    r = E.run_loop(k, b, run=f, mem=24, cpus=2)
    prd = [c for c, _ in f.calls if c[0] == "bash" and c[1].endswith("prd_run.sh")][0]
    assert prd[4] == "33" and r["mem_gb"] == 33 and r["mem_requested_gb"] == 24 and r["kit_peak_gb"] > 21
    assert "at 33 GB docker cap" in r["iterations"][0]["reason"]

class Sig11(Fake):
    """the first prd_run dies with the FlexPA SIGSEGV (run_prd.log), the retry passes"""

    def __init__(self, results):
        super().__init__(results)
        self.crashed = False

    def __call__(self, cmd, **kw):
        if cmd[0] == "bash" and cmd[1].endswith("prd_run.sh") and not self.crashed:
            self.calls.append((cmd, kw.get("env") or {}))
            self.crashed = True
            Path(cmd[2], "run_prd.log").write_text("Signal 11 received\n 6# drt::FlexPA::getEdgeCost(...)\n")
            return 2
        return super().__call__(cmd, **kw)


def test_flexpa_sig11_retried_once_with_placement_repair_rc(tmp_path):
    k = kit(tmp_path)
    f = Sig11([rec(5, 5)])
    res = E.run_loop(k, base_rec(k, rec(-20, 2, slew=7)), tmp_path / "eco", run=f, tools=Path(E.HERE))
    assert res["verdict"] == "PASS"
    assert [i["status"] for i in res["iterations"]] == ["ERROR", "SIGNED"]
    assert res["iterations"][0]["flexpa_sig11"] and res["iterations"][1]["dir"].endswith("/i1r")
    runs = [env for cmd, env in f.calls if cmd[0] == "bash" and cmd[1].endswith("prd_run.sh")]
    assert "OT_PRD_REPAIR_RC" not in runs[0] and runs[1]["OT_PRD_REPAIR_RC"] == "placement"


def test_non_sig11_route_failure_not_retried(tmp_path):
    k = kit(tmp_path)
    res = E.run_loop(k, base_rec(k, rec(-20, 2)), tmp_path / "eco", run=Fake([None]), tools=Path(E.HERE))
    assert res["verdict"] == "ERROR" and len(res["iterations"]) == 1 and "repair_rc_retry" not in res


class Stale(Fake):
    """the first ECO session stops with OT_PRD STAGE_MISMATCH (seed DB older than the kit's post-route ECO SPEF)"""

    def __init__(self, results):
        super().__init__(results)
        self.hit = False

    def __call__(self, cmd, **kw):
        if cmd[0] == "bash" and cmd[1].endswith("prd_run.sh") and not self.hit:
            self.calls.append((cmd, kw.get("env") or {}))
            self.hit = True
            Path(cmd[2], "run_prd.log").write_text("Error: OT_PRD STAGE_MISMATCH: 1305 of 91669 SPEF logic instances\n")
            return 2
        return super().__call__(cmd, **kw)


def test_stage_mismatch_retried_once_from_final(tmp_path):
    k = kit(tmp_path)
    f = Stale([rec(5, 5)])
    res = E.run_loop(k, base_rec(k, rec(-20, 2)), tmp_path / "eco", run=f, tools=Path(E.HERE))
    assert res["verdict"] == "PASS" and "stage_retry" in res
    assert [i["status"] for i in res["iterations"]] == ["ERROR", "SIGNED"]
    assert res["iterations"][0]["stage_mismatch"] and res["iterations"][1]["dir"].endswith("/i1f")
    runs = [env for cmd, env in f.calls if cmd[0] == "bash" and cmd[1].endswith("prd_run.sh")]
    assert runs[0]["OT_PRD_FROM"] == "route" and runs[1]["OT_PRD_FROM"] == "final"


def test_stage_mismatch_on_grt_mode_not_retried(tmp_path):
    k = kit(tmp_path)
    res = E.run_loop(k, base_rec(k, rec(-20, 2, drc=3)), tmp_path / "eco", run=Stale([rec(5, 5)]),
                     tools=Path(E.HERE))
    assert res["verdict"] == "ERROR" and len(res["iterations"]) == 1 and "stage_retry" not in res


def test_eco_vclk_frame_uses_signoff_measured(tmp_path, monkeypatch):
    ref = "applied mode pin_flop_mean clock vclk latency_ps 332.271532 samples 232 missing 0 clocks 1"
    assert E.measured_vclk(ref) == pytest.approx(332.271532)
    assert E.measured_vclk("applied mode bound_ff clock vclk latency_ps 342") is None
    assert E.measured_vclk(None) is None
    r = rec(1, -4)
    r["checks"]["hold_ff"]["ff_vclk_reference"] = ref
    r["checks"]["setup_tt"]["vclk_reference"] = ref.replace("332.271532", "437.8")
    prev = E.metrics(r)
    (tmp_path / "config.mk").write_text("export OT_VCLK_FF = 342\n")
    assert E.eco_vclk_frame(tmp_path, "b10", prev) == pytest.approx(332.271532)
    assert "OT_ECO_VCLK_PS = 332.271532" in (tmp_path / "config.mk").read_text()
    assert E.eco_vclk_frame(tmp_path, "t10", prev) == pytest.approx(437.8)
    assert E.eco_vclk_frame(tmp_path, "m10", prev) is None             # two-mode has its own measured frame
    assert E.eco_vclk_frame(tmp_path, "b10", E.metrics(rec(1, -4))) is None  # unmeasured: kit bound stays
    monkeypatch.setenv("OT_ECO_MEASURED_VCLK", "0")
    assert E.eco_vclk_frame(tmp_path, "b10", prev) is None


# KW-FIX-16 11-05 (COORD URGENT, intel2 scratch2 ~1 GB/min): once a later ECO pass is staged, every earlier finished
# pass drops 5_route / 5_3_fillcell / 6_1_fill odbs; 6_final, seeds (5_2_route / 5_1_grt), SIGNED passes stay.
class OdbFake(Fake):
    def __call__(self, cmd, **kw):
        rc = super().__call__(cmd, **kw)
        if cmd[0] == "bash" and cmd[1].endswith("prd_run.sh") and rc == 0:
            b = Path(cmd[2]) / "run/results/asap7/n/base"
            for f in ("5_1_grt.odb", "5_2_route.odb", "5_route.odb", "5_3_fillcell.odb", "6_1_fill.odb", "6_final.odb"):
                (b / f).write_text("odb")
        return rc


def test_superseded_pass_odbs_trimmed_when_next_pass_staged(tmp_path, monkeypatch, three_iter):
    monkeypatch.delenv("OT_ECO_KEEP_ROUTED", raising=False)
    k = kit(tmp_path, mm=False)
    b = base_rec(k, rec(-6, -2, slew=0))
    f = OdbFake([rec(-3, -1), rec(-1, -1), rec(1, 2)])
    r = E.run_loop(k, b, run=f, mem=8, cpus=2, **three_iter)
    assert r["verdict"] == "PASS" and len(r["iterations"]) == 3
    trimmed = [x for it in r["iterations"] for x in it.get("trimmed", [])]
    by = {}
    for x in trimmed:
        by.setdefault(Path(x).parents[5].name, set()).add(Path(x).name)
    # KW-FIX-24: the best (final) dir i3 also drops them once its 6_final.odb exists (trim_best)
    assert by == {d: {"5_route.odb", "5_3_fillcell.odb", "6_1_fill.odb"} for d in ("i1t", "i1", "i2t", "i2", "i3t", "i3")}
    last = Path(r["root"]) / "i3" / "run/results/asap7/n/base"
    names = {p.name for p in last.iterdir()}
    assert "6_final.odb" in names and not names & {"5_route.odb", "5_3_fillcell.odb", "6_1_fill.odb"}
    # keep (debug runs) keeps everything
    k2 = kit(tmp_path / "k2", mm=False)
    r2 = E.run_loop(k2, base_rec(k2, rec(-6, -2, slew=0)), run=OdbFake([rec(-3, -1), rec(1, 2)]), mem=8, cpus=2, keep=True, **three_iter)
    assert not any(it.get("trimmed") for it in r2["iterations"])
    assert (Path(r2["root"]) / "i1t/run/results/asap7/n/base/5_route.odb").exists()


def test_trim_skips_signed_unfinished_and_switch(tmp_path, monkeypatch):
    monkeypatch.delenv("OT_ECO_KEEP_ROUTED", raising=False)
    root = tmp_path / "eco"
    names = ("5_route.odb", "5_3_fillcell.odb", "6_1_fill.odb")
    for d, final, signed in (("i1", True, True), ("i2", False, False), ("i3", True, False), ("i4", True, False)):
        b = root / d / "run/results/asap7/n/base"
        b.mkdir(parents=True)
        for n in names + (("6_final.odb",) if final else ()):
            (b / n).write_text("x")
        if signed:
            (root / d / "signoff").mkdir()
            (root / d / "signoff/signoff.json").write_text(json.dumps(rec(1, 1)))
    monkeypatch.setenv("OT_ECO_KEEP_ROUTED", "1")
    assert E.trim_superseded(root, root / "i4") == []
    monkeypatch.delenv("OT_ECO_KEEP_ROUTED")
    gone = E.trim_superseded(root, root / "i4")
    assert sorted(Path(g).parent.parent.parent.parent.parent.parent.name for g in gone) == ["i3"] * 3
    assert all((root / d / "run/results/asap7/n/base" / n).exists() for d in ("i1", "i2", "i4") for n in names)


def test_relative_output_is_absolute_for_abstract_docker_mount(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    k = kit(tmp_path)
    b = base_rec(k, rec(-4, -2, slew=1))
    f = Fake([rec(1, 2)])
    def stage(_kit, root, tools):
        (root / "so" / "tools").mkdir(parents=True)
        # The isolated staging stub still provides the repair scope the late ECO now requires.
        for name in ("orfs_hold_mm.tcl", "orfs_hold_mm.py"):
            shutil.copyfile(E.HERE.parent / name, root / "so" / "tools" / name)
        return root / "so"
    monkeypatch.setattr(E, "stage_so", stage)
    result = E.run_loop("kit", b.relative_to(tmp_path), root="kit/eco_relative", run=f, mem=8, cpus=2)
    assert result["verdict"] == "PASS"
    assert Path(result["root"]) == tmp_path / "kit/eco_relative"
    assert Path(result["base_signoff"]).is_absolute()
    abstract = [cmd for cmd, _ in f.calls if "do-generate_abstract" in " ".join(cmd)]
    assert abstract
    for cmd in abstract:
        for index, arg in enumerate(cmd[:-1]):
            if arg == "-v":
                assert Path(cmd[index + 1].split(":")[0]).is_absolute(), cmd


def test_terminal_abstract_failure_keeps_routed_recovery_pass(tmp_path, monkeypatch):
    k = kit(tmp_path)
    b = base_rec(k, rec(-4, -2, slew=1))
    class AbstractFail(Fake):
        def __call__(self, cmd, **kw):
            if 'do-generate_abstract' in ' '.join(str(c) for c in cmd):
                self.calls.append((cmd, kw.get('env') or {}))
                return 2
            return super().__call__(cmd, **kw)
    def stage(_kit, root, tools):
        (root / 'so').mkdir()
        return root / 'so'
    monkeypatch.setattr(E, 'stage_so', stage)
    r = E.run_loop(k, b, run=AbstractFail([rec(1, 2)]), mem=8, cpus=2)
    assert r['verdict'] == 'ERROR' and 'best' not in r
    assert r['recovery']['status'] == 'ERROR'
    for name in r['recovery']['pass_dirs']:
        assert (Path(name) / 'run/results').is_dir()
        assert (Path(name) / 'run/objects').is_dir()
    assert r['iterations'][-1]['retained_for_recovery']


# KW-FIX-24 11-06 (S81-ENGRR-B5): rc 137 is OOM only with OOM evidence; a docker stop / external signal is ABORTED
@pytest.mark.parametrize("rc,log,verdict", [
    (137, None, "ABORTED"),                                          # docker stop SIGKILL, no log line
    (137, "[INFO GRT-0001] reading\n", "ABORTED"),
    (-9, None, "ABORTED"),
    (143, None, "ABORTED"),                                          # docker stop SIGTERM
    (-15, "", "ABORTED"),
    (137, "[INFO] read_spef\nKilled\n", "ECO_OOM"),                 # memory evidence in the step log
    (137, "OOMKilled true\n", "ECO_OOM"),
    (143, "terminate called after std::bad_alloc\n", "ECO_OOM"),
    (1, None, "ERROR"),                                              # a real tool failure: unchanged
    (139, None, "ERROR"),                                            # SIGSEGV is the tool's own crash, not a stop
])
def test_eco_rc_mapping(tmp_path, rc, log, verdict):
    k = kit(tmp_path)
    b = base_rec(k, rec(5, -3))
    r = E.run_loop(k, b, run=OomFake(rc, log=log), mem=24, cpus=2)
    it = r["iterations"][0]
    assert r["verdict"] == verdict and it["status"] == verdict, (r["verdict"], it.get("reason"))
    assert json.loads((Path(r["root"]) / "eco_loop.json").read_text())["verdict"] == verdict
    if verdict == "ABORTED":
        assert f"stopped from outside (rc {rc}" in it["reason"]
        assert E.summary(r).startswith("late-ECO ABORTED")
    if verdict == "ERROR":
        assert "route / clock-freeze check / finish failed" in it["reason"]


def test_oom_evidence_needs_a_memory_line(tmp_path):
    p = tmp_path / "run.log"
    assert not E.oom_evidence(137) and not E.oom_evidence(-9)
    p.write_text("all fine\n")
    assert not E.oom_evidence(137, p)
    p.write_text("make: *** [do-route] Error 137\n")
    assert E.oom_evidence(2, p)


def _tools_copy(tmp_path, with_common_flow=True):
    """a standalone tools copy as lanes make it (tools/die_plan files, optionally physical/common_flow beside it)"""
    from common_flow_src import common_flow_file
    src = tmp_path / "tools_copy"
    dp = src / "tools" / "die_plan"
    dp.mkdir(parents=True)
    for p in E.HERE.iterdir():
        if p.is_file() and p.name != "clock_family.tcl":
            shutil.copy2(p, dp / p.name)
    if with_common_flow:
        cf = src / "physical" / "common_flow"
        cf.mkdir(parents=True)
        for name in E.COMMON_FLOW_BUNDLE:
            shutil.copy2(common_flow_file(name, E.HERE.parents[1]), cf / name)
    return dp


def test_stage_so_stages_common_flow_beside_die_plan(tmp_path):
    """KW-FIX-24: the staged SO tree carries physical/common_flow next to tools/die_plan, so its own signoff.py bundle
    (prd_mk.sh, every pass) resolves clock_family.tcl / macro_cts_cluster.tcl (formerly 'incomplete tool bundle')."""
    tools = _tools_copy(tmp_path)
    k = tmp_path / "kit"
    k.mkdir()
    (k / "config.mk").write_text("export DESIGN_NAME = x\n")
    so = E.stage_so(k, tmp_path / "eco", tools)
    cf = so / "physical" / "common_flow"
    for name in E.COMMON_FLOW_BUNDLE:
        assert (cf / name).read_bytes() == (tools.parents[1] / "physical/common_flow" / name).read_bytes()
    # prd_mk.sh: SO/tools/die_plan/signoff.py bundle OUT on a two-mode pass dir (orfs_hold_mm.tcl needs macro_cts_cluster)
    out = tmp_path / "pass"
    out.mkdir()
    (out / "orfs_hold_mm.tcl").write_text("# kit two-mode hook\n")
    r = subprocess.run([sys.executable, "-I", str(so / "tools/die_plan/signoff.py"), "bundle", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert (out / "macro_cts_cluster.tcl").read_bytes() == (cf / "macro_cts_cluster.tcl").read_bytes()
    assert (out / "clock_family.tcl").read_bytes() == (cf / "clock_family.tcl").read_bytes()


def test_stage_so_without_common_flow_names_the_gap(tmp_path):
    tools = _tools_copy(tmp_path, with_common_flow=False)
    k = tmp_path / "kit"
    k.mkdir()
    with pytest.raises(ValueError, match="physical/common_flow/clock_family.tcl"):
        E.stage_so(k, tmp_path / "eco", tools)


class Hang(Fake):
    """KW-FIX-24: the first prd_run sits in the route-keep incremental GRT (rip line, no restore, flat log) until the
    watchdog stops it (rc 137 as docker stop gives); the retry passes"""

    def __init__(self, results, stopped):
        super().__init__(results)
        self.hit, self.stopped = False, stopped

    def __call__(self, cmd, **kw):
        if cmd[0] == "bash" and cmd[1].endswith("prd_run.sh") and not self.hit:
            self.calls.append((cmd, kw.get("env") or {}))
            self.hit = True
            log = Path(cmd[2], "run_prd.log")
            log.write_text("OT_PRD_ROUTE_KEEP ripped 2412 nets (2412 selected: new 10, connectivity 2, ...)\n"
                           "[INFO GRT-0001] ...\n")
            os.utime(log, (1, 1))
            assert self.stopped.wait(10), "watchdog never stopped the hung pass"
            return 137
        return super().__call__(cmd, **kw)


def test_grt_hang_detection(tmp_path):
    log = tmp_path / "run_prd.log"
    assert E.grt_hang(log, 10) is None                                       # no log
    log.write_text("OT_PRD_ROUTE_KEEP ripped 37 nets (x)\n")
    assert E.grt_hang(log, 10) is None                                       # fresh log: still working
    os.utime(log, (1, 1))
    assert E.grt_hang(log, 10) == 37                                         # flat inside the incremental GRT
    log.write_text("OT_PRD_ROUTE_KEEP ripped 37 nets (x)\nOT_PRD_ROUTE_KEEP restore: re-attached 9\n")
    os.utime(log, (1, 1))
    assert E.grt_hang(log, 10) is None                                       # past the GRT: DRT may be long, not this class
    log.write_text("[INFO DRT] flat in detailed route, OT_PRD_FROM=grt\n")
    os.utime(log, (1, 1))
    assert E.grt_hang(log, 10) is None                                       # no route-keep: not this class


def test_grt_hang_stops_container_and_retries_full_route(tmp_path, monkeypatch):
    import threading
    monkeypatch.setattr(E, "GRT_FLAT_S", 5)
    monkeypatch.setattr(E, "WATCH_POLL_S", 0.05)
    stopped, seen = threading.Event(), []

    def stop(pd):
        seen.append(str(pd))
        stopped.set()
        return ["prd-eco-i1-123"]

    monkeypatch.setattr(E, "stop_eco_container", stop)
    k = kit(tmp_path)
    f = Hang([rec(5, 5)], stopped)
    res = E.run_loop(k, base_rec(k, rec(-20, 2)), tmp_path / "eco", run=f, tools=Path(E.HERE))
    assert res["verdict"] == "PASS" and "grt_hang_retry" in res
    assert [i["status"] for i in res["iterations"]] == ["ERROR", "SIGNED"]
    h = res["iterations"][0]["grt_hang"]
    assert h["rip"] == 2412 and h["stopped"] == ["prd-eco-i1-123"] and seen == [res["iterations"][0]["dir"]]
    assert "hung" in res["iterations"][0]["reason"] and res["iterations"][1]["dir"].endswith("/i1g")
    runs = [env for cmd, env in f.calls if cmd[0] == "bash" and cmd[1].endswith("prd_run.sh")]
    assert runs[0]["OT_PRD_FROM"] == "route" and runs[1]["OT_PRD_FROM"] == "grt"


def test_iterate_keep_route_false_never_route_keeps(tmp_path, monkeypatch):
    k = kit(tmp_path)
    monkeypatch.setattr(E, "passes", lambda kit, prev, hm: ["t0", "b0"])
    f = Fake([rec(5, 5)])
    so = E.stage_so(k, tmp_path / "so")
    E.iterate(1, k, tmp_path / "eco", k, None, so, "grt", 0, 8, 2, f, keep_route=False)
    runs = [env["OT_PRD_FROM"] for cmd, env in f.calls if cmd[0] == "bash" and cmd[1].endswith("prd_run.sh")]
    assert runs == ["grt", "grt"]


def test_stop_eco_container_stops_only_this_pass(tmp_path, monkeypatch):
    pd = tmp_path / "eco/i1"
    pd.mkdir(parents=True)
    (tmp_path / "link").symlink_to(tmp_path / "eco")
    calls = []

    class R:
        def __init__(self, out=""):
            self.stdout = out

    def run(cmd, **kw):
        calls.append(cmd)
        if cmd[1] == "ps":
            return R("aaa\nbbb\n")
        if cmd[1] == "inspect":
            src = tmp_path / "link/i1" if cmd[-1] == "aaa" else tmp_path / "eco/i2"
            return R(f"/prd-eco-i1-{cmd[-1]}\t{src}|/work /x|/y \n")
        return R()

    monkeypatch.setattr(E, "docker", lambda: "docker")
    monkeypatch.setattr(E.subprocess, "run", run)
    assert E.stop_eco_container(pd) == ["prd-eco-i1-aaa"]
    assert [c for c in calls if c[1] == "stop"] == [["docker", "stop", "-t", "30", "aaa"]]


class Odbs(Fake):
    """prd_mk / finish leave the ORFS route odbs in each pass dir (as a real ECO route does)"""

    def __call__(self, cmd, **kw):
        rc = super().__call__(cmd, **kw)
        if cmd[0] == "bash" and cmd[1].endswith("prd_run.sh") and rc == 0:
            b = Path(cmd[2]) / "run/results/asap7/n/base"
            b.mkdir(parents=True, exist_ok=True)
            for n in ("5_2_route.odb", "5_route.odb", "5_3_fillcell.odb", "6_1_fill.odb", "6_final.odb", "6_final.spef"):
                (b / n).write_text("odb\n")
        return rc


def test_best_dir_drops_superseded_route_odbs(tmp_path, monkeypatch):
    monkeypatch.delenv("OT_ECO_KEEP_ROUTED", raising=False)
    k = kit(tmp_path)
    res = E.run_loop(k, base_rec(k, rec(-20, 2)), tmp_path / "eco", run=Odbs([rec(5, 5)]), tools=Path(E.HERE))
    assert res["verdict"] == "PASS" and res["best_trimmed"] == 3
    b = Path(res["best"]["dir"]) / "run/results/asap7/n/base"
    assert sorted(p.name for p in b.iterdir()) == ["5_2_route.odb", "6_final.odb", "6_final.spef"]


def test_best_dir_trim_needs_final_and_honours_keep(tmp_path, monkeypatch):
    b = tmp_path / "i1/run/results/asap7/n/base"
    b.mkdir(parents=True)
    for n in ("5_route.odb", "5_3_fillcell.odb", "6_1_fill.odb"):
        (b / n).write_text("odb\n")
    it = {"dir": str(tmp_path / "i1")}
    assert E.trim_best(it) == []                                   # no 6_final.odb: the route DB is the routed DB
    (b / "6_final.odb").write_text("")
    assert E.trim_best(it) == []                                   # empty 6_final: not a DB
    (b / "6_final.odb").write_text("odb\n")
    monkeypatch.setenv("OT_ECO_KEEP_ROUTED", "1")
    assert E.trim_best(it) == []
    monkeypatch.delenv("OT_ECO_KEEP_ROUTED")
    assert len(E.trim_best(it)) == 3 and sorted(p.name for p in b.iterdir()) == ["6_final.odb"]


def _mixed_hold_record(tmp_path, census):
    """a FAIL hold record of -84.65 ps on 1425 endpoints, FF census given, near miss on every other gate"""
    (tmp_path / "ff").mkdir()
    (tmp_path / "ff" / "corner.json").write_text(json.dumps(dict(std_nviol_min=1425.0, std_min_start=census)))
    b = tmp_path / "signoff.json"
    return far(tt=5, ff=-84.65, ff_n=1425), b


MIXED = dict(port=1424.0, other=1.0, reg=1.0, trunc=0.0, err=0.0, ports=["a"])


def test_mixed_hold_scores_nonport_only(tmp_path):
    r, b = _mixed_hold_record(tmp_path, dict(MIXED, nonport_n=1.0, nonport_wns=-0.49))
    ok, beyond, warn = E.near_miss(r, b)
    assert ok and not beyond and any("1 endpoint(s) at -0.49" in x for x in warn)


def test_mixed_hold_core_split_excludes_output_endpoints(tmp_path):
    """COORD R4: output-port endpoints are the parent's in the sign-off census, so they leave the near-miss count"""
    c = dict(MIXED, oport=2000.0, nonport_n=2010.0, nonport_wns=-34.0, core_n=10.0, core_wns=-8.0)
    r, b = _mixed_hold_record(tmp_path, c)
    ok, beyond, warn = E.near_miss(r, b)
    assert ok and not beyond and any("10 endpoint(s) at -8.0" in x and "output ports" in x for x in warn)


def test_core_split_large_still_far(tmp_path):
    """the alignment is not an allowance: the same numbers on the remaining endpoints"""
    c = dict(MIXED, oport=2000.0, nonport_n=2200.0, nonport_wns=-34.0, core_n=200.0, core_wns=-31.0)
    r, b = _mixed_hold_record(tmp_path, c)
    ok, beyond, _ = E.near_miss(r, b)
    assert not ok and "hold WNS -31.0" in beyond[0] and "200 endpoints" in beyond[1]


def test_older_census_bounds_count_keeps_unsplit_wns(tmp_path):
    """no core_n: count bounded by other + reg, wns the unsplit non-port wns (the older census cannot split it)"""
    c = dict(MIXED, other=20.0, reg=20.0, oport=2000.0, nonport_n=2030.0, nonport_wns=-34.0)
    r, b = _mixed_hold_record(tmp_path, c)
    ok, beyond, warn = E.near_miss(r, b)
    assert not ok and "hold WNS -34.0" in beyond[0] and not any("endpoints" in x for x in beyond)
    assert any("older census" in x for x in warn)


def test_older_census_no_oport_is_exact(tmp_path):
    r, b = _mixed_hold_record(tmp_path, dict(MIXED, nonport_n=1.0, nonport_wns=-0.49, oport=0.0))
    ok, _, warn = E.near_miss(r, b)
    assert ok and not any("older census" in x for x in warn)


def test_mixed_hold_large_nonport_still_far(tmp_path):
    r, b = _mixed_hold_record(tmp_path, dict(MIXED, nonport_n=101.0, nonport_wns=-31.0))
    ok, beyond, _ = E.near_miss(r, b)
    assert not ok and "hold WNS -31.0" in beyond[0] and "101 endpoints" in beyond[1]


@pytest.mark.parametrize("census", [MIXED, dict(MIXED, nonport_n=1.0, nonport_wns=-0.49, err=1.0),
                                    dict(MIXED, nonport_n=1.0, nonport_wns=-0.49, trunc=1.0)])
def test_mixed_hold_no_split_scores_whole_number(tmp_path, census):
    r, b = _mixed_hold_record(tmp_path, census)
    ok, beyond, _ = E.near_miss(r, b)
    assert not ok and "hold WNS -84.65" in beyond[0] and "1425 endpoints" in beyond[1]


def test_superseded_full_copies_pruned_during_the_loop(tmp_path, monkeypatch, three_iter):
    """KW-FIX-32 11-07 (COORD 21:0x, epyc6 root: 13 S81 slice_station loops 165 GB): the t<N> pass's full ORFS copy
    goes once the iteration's final pass is routed (before its sign-off), and an iteration's final copy goes once a
    later iteration is adopted as best -- not only at loop end; the adopted copy, logs and every sign-off stay"""
    monkeypatch.delenv("OT_ECO_KEEP_ROUTED", raising=False)
    k = kit(tmp_path, mm=False)
    b = base_rec(k, rec(-6, -2, slew=0))
    seen = []

    class Spy(Fake):
        def __call__(self, cmd, **kw):
            if cmd[0] == "bash" and cmd[1].endswith("prd_mk.sh") or "--out" in cmd:
                root = Path(cmd[3]).parent if cmd[0] == "bash" else Path(cmd[cmd.index("--kit") + 1]).parent
                seen.append((Path(cmd[3]).name if cmd[0] == "bash" else "signoff:" + Path(cmd[cmd.index("--kit") + 1]).name,
                             sorted(d.name for d in root.glob("i*") if (d / "run/results").is_dir())))
            return super().__call__(cmd, **kw)

    r = E.run_loop(k, b, run=Spy([rec(-3, -1), rec(-1, -1), rec(1, 2)]), mem=8, cpus=2, **three_iter)
    assert r["verdict"] == "PASS" and r["best"]["n"] == 3
    at = dict(seen)
    assert at["signoff:i1"] == ["i1"]                 # i1t gone before i1's sign-off
    assert at["i2t"] == ["i1"]                        # i1 is the seed of iteration 2 and the best so far: kept
    assert at["signoff:i2"] == ["i1", "i2"]
    assert at["i3t"] == ["i2"]                        # i2 adopted over i1: i1's full copy went at once
    root = Path(r["root"])
    assert sorted(d.name for d in root.glob("i*") if (d / "run/results").is_dir()) == ["i3"]
    for n in ("i1", "i2", "i3"):
        assert (root / n / "signoff/signoff.json").is_file() and (root / n / "config_eco.mk").is_file()
    assert r["iterations"][0]["intermediate_pruned"] == [str(root / "i1t/run/results"), str(root / "i1t/run/objects")]
    # OT_ECO_KEEP_ROUTED=1 keeps every copy, as the end-of-loop prune does
    monkeypatch.setenv("OT_ECO_KEEP_ROUTED", "1")
    k2 = kit(tmp_path / "k2", mm=False)
    r2 = E.run_loop(k2, base_rec(k2, rec(-6, -2, slew=0)), run=Fake([rec(-3, -1), rec(1, 2)]), mem=8, cpus=2, keep=True,
                    **three_iter)
    assert (Path(r2["root"]) / "i1t/run/results").is_dir() and (Path(r2["root"]) / "i1/run/results").is_dir()


def _census_out(out, np_n, np_wns, port=100.0):
    """write the FF corner census the sign-off leaves next to signoff.json"""
    (out / "ff").mkdir(parents=True, exist_ok=True)
    sms = dict(port=port, other=float(np_n), reg=float(np_n), trunc=0.0, err=0.0, ports=["cr_i"])
    if np_n:
        sms.update(nonport_n=float(np_n), nonport_wns=float(np_wns))
    (out / "ff" / "corner.json").write_text(json.dumps(dict(std_min_start=sms)))


class FakeNP(Fake):
    """Fake whose sign-offs also leave an FF census: census[i] = (non-port endpoints, non-port WNS) of iteration i+1"""

    def __init__(self, results, census):
        super().__init__(results)
        self.census = list(census)

    def __call__(self, cmd, **kw):
        if "run" in cmd and "--out" in cmd:
            n, w = self.census[self.n]
            rc = super().__call__(cmd, **kw)
            _census_out(Path(cmd[cmd.index("--out") + 1]), n, w)
            return rc
        return super().__call__(cmd, **kw)


def test_nonport_scope_scores_nonport_hold(tmp_path, monkeypatch, three_iter):
    """KW-FIX-32 11-07 (COORD 21:4x (3), DIE-KV-91 M5 e1): with OT_HOLD_REPAIR_SCOPE=nonport a repair of the non-port
    hold (81 endpoints at -7.98 -> 1 at -0.05) is an improvement although the whole FF WNS (port starts, the parent's)
    barely moves; default scope keeps the whole-number rule."""
    k = kit(tmp_path, mm=False)
    b = base_rec(k, rec(33.7, -7.98))
    _census_out(k / "signoff", 81, -7.98)
    results = lambda: [rec(33.7, -7.10), rec(33.7, -7.05), rec(33.7, 1)]
    census = [(1, -0.05), (0, 0), (0, 0)]
    monkeypatch.setenv("OT_HOLD_REPAIR_SCOPE", "nonport")
    r = E.run_loop(k, b, run=FakeNP(results(), census), mem=8, cpus=2, root=tmp_path / "np", **three_iter)
    assert r["base_metrics"]["ff_np"] == -7.98 and r["base_metrics"]["ff_np_n"] == 81
    assert r["iterations"][0]["metrics"]["ff_np"] == -0.05 and r["iterations"][0]["metrics"]["ff_np_n"] == 1
    assert "no improvement at iteration 1" not in r["reason"] and len(r["iterations"]) >= 2
    assert r["iterations"][1]["metrics"]["ff_np"] == 0.0 and r["iterations"][1]["metrics"]["ff_np_n"] == 0
    assert "non-port -7.98/81->" in E.summary(r)
    # Explicit all retains the historical whole-number score; late default now owns core endpoints only.
    monkeypatch.setenv("OT_HOLD_REPAIR_SCOPE", "all")
    k2 = kit(tmp_path / "d", mm=False)
    b2 = base_rec(k2, rec(33.7, -7.98))
    _census_out(k2 / "signoff", 81, -7.98)
    r2 = E.run_loop(k2, b2, run=FakeNP(results(), census), mem=8, cpus=2, root=tmp_path / "dflt", **three_iter)
    assert "ff_np" not in r2["base_metrics"] and "ff_np" not in r2["iterations"][0]["metrics"]
    assert r2["verdict"] == "EXHAUSTED" and "no improvement at iteration 1" in r2["reason"]   # -7.98 -> -7.10 < 1 ps


def test_nonport_score_reads_census_or_falls_back(tmp_path, monkeypatch):
    so = tmp_path / "signoff.json"
    so.write_text("{}")
    assert E.nonport_score(so) is None                                          # no census
    _census_out(tmp_path, 3, -2.5)
    assert E.nonport_score(so) == (-2.5, 3)
    _census_out(tmp_path, 0, 0)
    assert E.nonport_score(so) == (0.0, 0)                                      # all port starts
    c = json.loads((tmp_path / "ff/corner.json").read_text())
    c["std_min_start"]["trunc"] = 1.0
    (tmp_path / "ff/corner.json").write_text(json.dumps(c))
    assert E.nonport_score(so) is None                                          # truncated census: whole number
    monkeypatch.setenv("OT_HOLD_REPAIR_SCOPE", "nonport")
    _census_out(tmp_path, 3, -2.5)
    m = E.metrics(rec(5, -9), so)
    assert m["ff"] == -9 and m["ff_np"] == -2.5 and m["ff_np_n"] == 3
    p = dict(m, ff_np=-2.0, ff_np_n=3)
    assert not E.improved(p, m) and E.better(p, m)                              # scored on the non-port number
    assert "ff_np" not in E.metrics(rec(5, -9))                                 # no path: whole number


def test_stage_so_read_only_tag_tools_with_kit_override(tmp_path):
    """DIE-KV-93 11-08 FLOW class: eco_loop on a tag tools tree (all 0444) with a kit .tcl of the same name
    (face_flops_release.tcl) failed EACCES in stage_so; the kit file must win and the staged tree stay writable."""
    tools = _tools_copy(tmp_path)
    (tools / "face_flops_release.tcl").write_text("# tag tool copy\n")
    k = tmp_path / "kit"
    k.mkdir()
    (k / "config.mk").write_text("export DESIGN_NAME = x\n")
    (k / "face_flops_release.tcl").write_text("# kit override\n")
    for p in list(tools.iterdir()) + list((tools.parents[1] / "physical" / "common_flow").iterdir()):
        if p.is_file():
            p.chmod(0o444)
    so = E.stage_so(k, tmp_path / "eco", tools)
    dp = so / "tools" / "die_plan"
    assert (dp / "face_flops_release.tcl").read_text() == "# kit override\n"
    assert (tools / "face_flops_release.tcl").read_text() == "# tag tool copy\n"
    assert all(os.access(p, os.W_OK) for p in dp.iterdir() if p.is_file())
    E.stage_so(k, tmp_path / "eco", tools)          # re-staging over the existing tree works too


def test_hold_repair_target_default_is_5():
    """COORD 11-09 stopgap: the repair aims 5 ps above 0; the gate (FF hold slack >= 0) does not use this number."""
    assert E.HOLD_MARGIN_PS == 5



# KW-FIX-44 11-09 (HBM-COLLECT-1/N4-C 10:54): a two-mode kit whose orfs_hold_mm.tcl predates the hold-repair scope.
STALE_MM_TCL = "# kit two-mode hook, before HOLD-REPAIR-SCOPE\nproc ot_hold_stage {} { return 4_cts.sdc }\n"
R2R_MM_TCL = "# reg2reg-era hook\nproc ot_hold_repair_scope {body} { uplevel 1 $body }\n"


def _mm_kit(tmp_path, tcl, scope="nonport"):
    k = tmp_path / "kit"
    k.mkdir(parents=True)
    (k / "config.mk").write_text("export DESIGN_NAME = x\noverride export OT_HOLD_MM = 1\n"
                                 + (f"export OT_HOLD_REPAIR_SCOPE = {scope}\n" if scope else ""))
    (k / "orfs_hold_mm.tcl").write_text(tcl)
    (k / "orfs_hold_mm.py").write_text("# kit patcher\n")
    return k


def test_hold_mm_supports_reads_the_declared_modes(tmp_path):
    t = tmp_path / "o.tcl"
    assert not E.hold_mm_supports(t, "nonport")                                   # missing file
    t.write_text(STALE_MM_TCL)
    assert not E.hold_mm_supports(t, "nonport") and not E.hold_mm_supports(t, "reg2reg")
    t.write_text(R2R_MM_TCL)
    assert not E.hold_mm_supports(t, "reg2reg") and not E.hold_mm_supports(t, "nonport")
    assert E.hold_mm_supports(E.HERE.parent / "orfs_hold_mm.tcl", "nonport")    # the current tools copy
    assert E.hold_mm_supports(E.HERE.parent / "orfs_hold_mm.tcl", "reg2reg")


def test_kit_hold_scope_env_then_config(tmp_path, monkeypatch):
    monkeypatch.delenv("OT_HOLD_REPAIR_SCOPE", raising=False)
    k = _mm_kit(tmp_path, STALE_MM_TCL, scope="nonport")
    assert E.kit_hold_scope(k) == "nonport" and E.hold_mm_scope_needed(k) == "nonport"
    monkeypatch.setenv("OT_HOLD_REPAIR_SCOPE", "reg2reg")
    assert E.kit_hold_scope(k) == "reg2reg"
    monkeypatch.delenv("OT_HOLD_REPAIR_SCOPE")
    (k / "config.mk").write_text("export OT_HOLD_REPAIR_SCOPE = nonport\n")      # single-mode kit: no orfs_hold_mm
    assert E.hold_mm_scope_needed(k) == ""


def test_stage_so_stages_current_hold_mm_over_a_stale_kit_copy(tmp_path, monkeypatch):
    monkeypatch.delenv("OT_HOLD_REPAIR_SCOPE", raising=False)
    k = _mm_kit(tmp_path, STALE_MM_TCL)
    so = E.stage_so(k, tmp_path / "eco")
    for n in E.HOLD_MM_FILES:   # the pair, both from the tools: a new .tcl never runs under the kit's old patcher
        assert (so / "tools" / n).read_bytes() == (E.HERE.parent / n).read_bytes()


def test_stage_so_keeps_a_kit_copy_that_supports_the_scope_or_has_no_scope(tmp_path, monkeypatch):
    monkeypatch.delenv("OT_HOLD_REPAIR_SCOPE", raising=False)
    good = STALE_MM_TCL + "set ::ot_hold_scope_supported_modes {reg2reg nonport}\n"
    k = _mm_kit(tmp_path / "a", good)
    assert (E.stage_so(k, tmp_path / "a" / "eco") / "tools/orfs_hold_mm.tcl").read_text() == good
    k = _mm_kit(tmp_path / "b", STALE_MM_TCL, scope="")                          # no scope asked: unchanged
    assert (E.stage_so(k, tmp_path / "b" / "eco") / "tools/orfs_hold_mm.tcl").read_text() == STALE_MM_TCL


def test_stage_so_refuses_when_no_copy_supports_the_scope(tmp_path, monkeypatch):
    monkeypatch.delenv("OT_HOLD_REPAIR_SCOPE", raising=False)
    tools = _tools_copy(tmp_path)
    (tools.parent / "orfs_hold_mm.tcl").write_text(STALE_MM_TCL)
    (tools.parent / "orfs_hold_mm.py").write_text("# old patcher\n")
    k = _mm_kit(tmp_path / "k", STALE_MM_TCL)
    with pytest.raises(ValueError, match="OT_HOLD_REPAIR_SCOPE=nonport"):
        E.stage_so(k, tmp_path / "eco", tools)


class StaleMM(Fake):
    """prd_mk.sh as on n4_local_vA: the pass dir carries the kit's pre-scope orfs_hold_mm.{py,tcl}"""

    def __call__(self, cmd, **kw):
        rc = super().__call__(cmd, **kw)
        if cmd[0] == "bash" and cmd[1].endswith("prd_mk.sh"):
            d = Path(cmd[3])
            (d / "orfs_hold_mm.tcl").write_text(STALE_MM_TCL)
            (d / "orfs_hold_mm.py").write_text("# kit patcher\n")
            (d / "config.mk").write_text("override export OT_HOLD_MM = 1\nexport OT_HOLD_REPAIR_SCOPE = nonport\n")
        if cmd[0] == "bash" and cmd[1].endswith("prd_run.sh"):
            self.mm_at_run = Path(cmd[2], "orfs_hold_mm.tcl").read_text()
        return rc


def test_run_loop_refreshes_the_pass_dir_hold_mm_before_prd_run(tmp_path, monkeypatch):
    """N4-C: both n4_local_vA ECOs routed 30 min, then prd_hook.tcl refused the unscoped repair.  The pass dir now gets the
    current pair after prd_mk.sh, before the physical run, and the record says so."""
    monkeypatch.delenv("OT_HOLD_REPAIR_SCOPE", raising=False)
    k = _mm_kit(tmp_path, STALE_MM_TCL)
    (k / "signoff").mkdir()
    (k / "signoff.py").write_text("# kit sign-off\n")
    fake = StaleMM([rec(5, 5)])
    r = E.run_loop(k, base_rec(k, rec(-5, -2)), tmp_path / "eco", run=fake, strict_one_pass=True, keep=True)
    assert fake.mm_at_run == (E.HERE.parent / "orfs_hold_mm.tcl").read_text()
    it = r["iterations"][0]
    assert sorted(sum(it["hold_mm_refreshed"].values(), [])) == sorted(E.HOLD_MM_FILES)
    assert r["verdict"] == "PASS"


def test_run_loop_errors_before_any_route_when_no_copy_supports_the_scope(tmp_path, monkeypatch):
    monkeypatch.delenv("OT_HOLD_REPAIR_SCOPE", raising=False)
    tools = _tools_copy(tmp_path / "t")
    (tools.parent / "orfs_hold_mm.tcl").write_text(STALE_MM_TCL)
    k = _mm_kit(tmp_path, STALE_MM_TCL)
    (k / "signoff").mkdir()
    fake = Fake([rec(5, 5)])
    r = E.run_loop(k, base_rec(k, rec(-5, -2)), tmp_path / "eco", run=fake, tools=tools)
    assert r["verdict"] == "ERROR" and "no iteration used" in r["reason"] and not r["iterations"]
    assert not [c for c, _ in fake.calls if c[0] == "bash"]


def test_postroute_lec_falls_back_to_the_tools_lec_py(tmp_path):
    """KW-FIX-44 11-09 (own_RF4T eco1b): a kit without lec.py runs the current tools' lec.py; a kit copy or --lec-tool wins"""
    k = kit(tmp_path)
    assert E.lec_tool_of(k) == E.HERE / "lec.py"
    (k / "lec.py").write_text("# kit lec\n")
    assert E.lec_tool_of(k) == k / "lec.py"
    t = tmp_path / "mine_lec.py"
    t.write_text("#\n")
    assert E.lec_tool_of(k, str(t)) == t
    d = tmp_path / "eco"
    (d / "base").mkdir(parents=True)
    res = {"root": str(d), "best": {"dir": str(d), "base": str(d / "base")}}
    (k / "lec.py").unlink()
    seen = []
    def passed(cmd, **kw):
        seen.append(cmd[1])
        (Path(cmd[cmd.index("--out") + 1]) / "lec.json").write_text(json.dumps({"verdict": "EQUIVALENT"}))
        return 0
    assert E.run_lec(k, res, 8, 2, run=passed) and seen == [str(E.HERE / "lec.py")]


def test_postroute_lec_without_any_lec_py_is_a_named_tool_gap(tmp_path):
    k = kit(tmp_path)
    empty = tmp_path / "tools"
    empty.mkdir()
    d = tmp_path / "eco"
    d.mkdir()
    res = {"root": str(d), "best": {"dir": str(d), "base": str(d)}}
    ran = []
    assert not E.run_lec(k, res, 8, 2, run=lambda *a, **k: ran.append(a) or 0, tools=empty)
    assert not ran and res["lec"]["verdict"] == "NO_LEC_TOOL" and "not a design verdict" in res["lec"]["reason"]
    assert json.loads((d / "eco_loop.json").read_text())["lec"]["verdict"] == "NO_LEC_TOOL"
