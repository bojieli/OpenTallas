"""KW-ECO-1: loop control of tools/die_plan/eco_loop.py (late-stage ECO on a routed DB) with a fake runner (no
OpenROAD): eligibility, stop rules (PASS / no improvement / max iterations / error), best pick + pruning, record."""
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import eco_loop as E  # noqa: E402


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
    assert mk2[2] == r["iterations"][0]["dir"] and mk2[4] == "m10"
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
    assert r["iterations"][0]["variant"] == "t10+b10"                        # TT slew + FF hold: both passes
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
    assert [c[4] for c in mk] == ["t10", "b10"]
    assert mk[0][3].endswith("/i1t") and mk[1][2] == mk[0][3] and mk[1][3] == it["dir"]
    envs = [e for c, e in f.calls if c[0] == "bash" and c[1].endswith("prd_run.sh")]
    assert envs[1]["OT_PRD_FROM"] == "route"
    # the b pass and the sign-off start from the kit's own config; the t pass dir is pruned, the final dir kept
    assert (Path(mk[0][3]) / "config.mk").read_text() == (k / "config.mk").read_text()
    assert not (Path(mk[0][3]) / "run/results").exists() and (Path(it["dir"]) / "run/results").exists()
    assert set(it["rc"]) >= {"prd_mk_t", "prd_run_t", "prd_mk_b", "prd_run_b", "signoff"}
