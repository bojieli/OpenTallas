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
            return 0
        if cmd[0] == "bash" and cmd[1].endswith("prd_run.sh"):
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


def test_pass_on_second_iteration(tmp_path):
    k = kit(tmp_path)
    b = base_rec(k, rec(-12, -13, slew=72))
    f = Fake([rec(-4, -6, slew=10), rec(1, 2)])
    r = E.run_loop(k, b, run=f, mem=8, cpus=2)
    assert r["verdict"] == "PASS" and len(r["iterations"]) == 2
    assert r["best"]["n"] == 2 and Path(r["best"]["signoff"]).is_file()
    assert r["kind"] == "eco" and r["base_routed_db"] == "/x/base/6_final.odb" and r["flow"]["tools_sha256"]
    assert all(it["commands"] for it in r["iterations"])
    # iteration 2 starts from iteration 1's routed dir; the superseded iteration 1 run data is pruned, best kept
    mk2 = [c for c, _ in f.calls if c[0] == "bash" and c[1].endswith("prd_mk.sh")][1]
    assert mk2[2] == r["iterations"][0]["dir"] and mk2[4] == "m0"
    assert not (Path(r["iterations"][0]["dir"]) / "run/results").exists()
    assert (Path(r["best"]["dir"]) / "run/results").exists()
    # sign-off on the kit's own config.mk (ECO overrides kept aside as config_eco.mk)
    d = Path(r["best"]["dir"])
    assert (d / "config.mk").read_text() == (k / "config.mk").read_text()
    assert (d / "config_eco.mk").read_text() == "eco overrides\n"
    assert json.loads((Path(r["root"]) / "eco_loop.json").read_text())["verdict"] == "PASS"
    # every ECO pass: route-keeping incremental DRT, finish only (the loop signs off itself)
    env = [e for c, e in f.calls if c[0] == "bash" and c[1].endswith("prd_run.sh")][0]
    assert env["OT_PRD_FROM"] == "route" and env["OT_PRD_POST"] == "0"


def test_no_improvement_stops_and_keeps_best(tmp_path):
    k = kit(tmp_path, mm=False)
    b = base_rec(k, rec(10, -8, slew=40))
    f = Fake([rec(10, -3, slew=5), rec(10, -2.6, slew=6), rec(10, 1)])
    r = E.run_loop(k, b, run=f, mem=8, cpus=2)
    assert r["verdict"] == "EXHAUSTED" and len(r["iterations"]) == 2 and "no improvement" in r["reason"]
    assert r["best"]["n"] == 2                                                 # -2.6 is better than -3
    assert r["iterations"][0]["variant"] == "t0+b0"                          # TT slew + FF hold: both passes
    s = E.summary(r)
    assert s.startswith("late-ECO exhausted (2 it") and "FF -8->-2.6" in s


def test_max_iterations(tmp_path):
    k = kit(tmp_path)
    b = base_rec(k, rec(-30, -20))
    f = Fake([rec(-20, -20), rec(-10, -20), rec(-5, -20), rec(5, 5)])
    r = E.run_loop(k, b, run=f, mem=8, cpus=2)
    assert r["verdict"] == "EXHAUSTED" and len(r["iterations"]) == E.MAX_ITER and r["best"]["n"] == 3
    assert "3 iterations" in r["reason"]


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
            (d / "run_kit_hbm.sh").write_text('if [ "$GOAL" = post ]; then :; fi\n')
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
    assert [c[4] for c in mk] == ["t0", "b0"]
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
    res = E.run_loop(k, base_rec(k, rec(-80, 2, slew=7)), tmp_path / "eco", run=f, tools=Path(E.HERE))
    assert res["verdict"] == "PASS"
    assert [i["status"] for i in res["iterations"]] == ["ERROR", "SIGNED"]
    assert res["iterations"][0]["flexpa_sig11"] and res["iterations"][1]["dir"].endswith("/i1r")
    runs = [env for cmd, env in f.calls if cmd[0] == "bash" and cmd[1].endswith("prd_run.sh")]
    assert "OT_PRD_REPAIR_RC" not in runs[0] and runs[1]["OT_PRD_REPAIR_RC"] == "placement"


def test_non_sig11_route_failure_not_retried(tmp_path):
    k = kit(tmp_path)
    res = E.run_loop(k, base_rec(k, rec(-80, 2)), tmp_path / "eco", run=Fake([None]), tools=Path(E.HERE))
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
    res = E.run_loop(k, base_rec(k, rec(-80, 2)), tmp_path / "eco", run=f, tools=Path(E.HERE))
    assert res["verdict"] == "PASS" and "stage_retry" in res
    assert [i["status"] for i in res["iterations"]] == ["ERROR", "SIGNED"]
    assert res["iterations"][0]["stage_mismatch"] and res["iterations"][1]["dir"].endswith("/i1f")
    runs = [env for cmd, env in f.calls if cmd[0] == "bash" and cmd[1].endswith("prd_run.sh")]
    assert runs[0]["OT_PRD_FROM"] == "route" and runs[1]["OT_PRD_FROM"] == "final"


def test_stage_mismatch_on_grt_mode_not_retried(tmp_path):
    k = kit(tmp_path)
    res = E.run_loop(k, base_rec(k, rec(-80, 2, drc=3)), tmp_path / "eco", run=Stale([rec(5, 5)]),
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


def test_superseded_pass_odbs_trimmed_when_next_pass_staged(tmp_path, monkeypatch):
    monkeypatch.delenv("OT_ECO_KEEP_ROUTED", raising=False)
    k = kit(tmp_path, mm=False)
    b = base_rec(k, rec(-6, -2, slew=0))
    f = OdbFake([rec(-3, -1), rec(-1, -1), rec(1, 2)])
    r = E.run_loop(k, b, run=f, mem=8, cpus=2)
    assert r["verdict"] == "PASS" and len(r["iterations"]) == 3
    trimmed = [x for it in r["iterations"] for x in it.get("trimmed", [])]
    by = {}
    for x in trimmed:
        by.setdefault(Path(x).parents[5].name, set()).add(Path(x).name)
    assert by == {d: {"5_route.odb", "5_3_fillcell.odb", "6_1_fill.odb"} for d in ("i1t", "i1", "i2t", "i2", "i3t")}
    last = Path(r["root"]) / "i3" / "run/results/asap7/n/base"
    assert {p.name for p in last.iterdir()} >= {"5_route.odb", "6_1_fill.odb", "6_final.odb"}
    # keep (debug runs) keeps everything
    k2 = kit(tmp_path / "k2", mm=False)
    r2 = E.run_loop(k2, base_rec(k2, rec(-6, -2, slew=0)), run=OdbFake([rec(-3, -1), rec(1, 2)]), mem=8, cpus=2, keep=True)
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
        (root / "so").mkdir()
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
    res = E.run_loop(k, base_rec(k, rec(-80, 2)), tmp_path / "eco", run=f, tools=Path(E.HERE))
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
