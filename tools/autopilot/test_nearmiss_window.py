#!/usr/bin/env python3
"""COORD 11-22 ruling (NEARMISS-ECO-R1 AUTO-ECO gap): R-MINIMAL near-miss window in autopilot.classify (1) and
auto_resign.judge_eco (2), and the one-time late-ECO retry after a tool ERROR (3)."""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


@pytest.fixture
def ap(monkeypatch, tmp_path):
    monkeypatch.setenv("OT_SIGNOFF_PROFILE", "minimal")
    monkeypatch.setenv("AP_DIR", str(tmp_path))
    monkeypatch.setenv("AP_RELEASE_CACHE", str(tmp_path / "rc.json"))
    import autopilot
    return autopilot


def census(core_wns, core_n):
    return {"done": True, "rc": 0, "errors": [], "std_min_start": {"err": 0, "trunc": 0, "core_wns": core_wns, "core_n": core_n}}


def job(tt=5.0, ff=-3.0, fails=("hold_ff",), drc=0, tt_n=0, ff_census=None, overflow=0):
    so = {"path": "/k/signoff/signoff.json", "verdict": "NOT SIGNED", "reasons": ["r"], "fails": list(fails), "tt_wns": tt,
          "ff_wns": ff, "tt_n": tt_n, "drc": drc, "pg": "PASS", "odb": "/k/run/x/6_final.odb", "base": "/k/run/x"}
    if ff_census is not None:
        so["ff_census"] = ff_census
    return {"signoff": so, "grt_overflow": overflow}


def test_internal_hold_window_uses_census_not_port_hold(ap):
    # whole FF -120 (port paths) but internal -22.5 on 188: the slw_stm_v2 case went to DONE-STRUCTURAL under -30 whole-FF
    assert ap.classify(job(ff=-120.0, ff_census=census(-22.5, 188)), {})[0] == "NEAR-MISS"
    assert ap.classify(job(ff=-120.0, ff_census=census(-45.0, 3)), {})[0] == "STRUCTURAL"
    assert ap.classify(job(ff=-120.0), {})[0] == "STRUCTURAL"          # no census: whole FF is the bound


def test_setup_window(ap):
    assert ap.classify(job(tt=-70.0, ff=2.0, fails=("setup_tt",), tt_n=300), {})[0] == "NEAR-MISS"
    assert ap.classify(job(tt=-90.0, ff=2.0, fails=("setup_tt",), tt_n=12), {})[0] == "NEAR-MISS"
    assert ap.classify(job(tt=-90.0, ff=2.0, fails=("setup_tt",), tt_n=30), {})[0] == "STRUCTURAL"
    assert ap.classify(job(tt=-553.13, ff=-107.0, fails=("setup_tt", "hold_ff"), tt_n=400), {})[0] == "STRUCTURAL"


def test_drc_overflow_and_structural_checks(ap):
    assert ap.classify(job(drc=50), {})[0] == "NEAR-MISS"
    assert ap.classify(job(drc=51), {})[0] == "STRUCTURAL"
    assert ap.classify(job(overflow=7), {})[0] == "STRUCTURAL"
    for f in ("clock", "unconstrained"):                                  # advisory under R-MINIMAL
        assert ap.classify(job(fails=("hold_ff", f)), {})[0] == "NEAR-MISS", f
    for f in ("sdc_lint", "face_guard"):
        assert ap.classify(job(fails=("hold_ff", f)), {})[0] == "STRUCTURAL", f


def test_legacy_profile_unchanged(ap, monkeypatch):
    monkeypatch.setenv("OT_SIGNOFF_PROFILE", "legacy")
    assert ap.classify(job(ff=-35.0, ff_census=census(-5.0, 2)), {})[0] == "STRUCTURAL"
    assert ap.classify(job(ff=-29.0), {})[0] == "NEAR-MISS"


def eco_probe(**kw):
    e = dict(record="/k/signoff/signoff.json", name="t", fails=["hold_ff"], tt=5.0, ff=-120.0, tt_n=0, ff_n=900, drc=0,
             odb_sha="a" * 64, kit="/k")
    e.update(kw)
    return e


def test_judge_eco_minimal_window(monkeypatch):
    monkeypatch.setenv("OT_SIGNOFF_PROFILE", "minimal")
    import auto_resign as AR
    c = dict(die="qwen_compute", name="t")
    assert AR.judge_eco(c, eco_probe(ff_core=-22.5, ff_core_n=188), {}, [], -30.0, 50)[0] == "LAUNCH"
    assert AR.judge_eco(c, eco_probe(ff_core=-41.0, ff_core_n=2), {}, [], -30.0, 50)[0] == "SKIP"
    assert AR.judge_eco(c, eco_probe(fails=["setup_tt", "clock"], tt=-70.0, tt_n=200, ff=1.0), {}, [], -30.0, 50)[0] == "LAUNCH"
    assert AR.judge_eco(c, eco_probe(fails=["setup_tt"], tt=-95.0, tt_n=40, ff=1.0), {}, [], -30.0, 50)[0] == "SKIP"
    assert AR.judge_eco(c, eco_probe(fails=["hold_ff", "sdc_lint"], ff_core=-1.0, ff_core_n=1), {}, [], -30.0, 50)[0] == "SKIP"


def test_judge_eco_legacy_window(monkeypatch):
    monkeypatch.setenv("OT_SIGNOFF_PROFILE", "legacy")
    import auto_resign as AR
    c = dict(die="qwen_compute", name="t")
    assert AR.judge_eco(c, eco_probe(ff_core=-22.5, ff_core_n=188), {}, [], -30.0, 50)[0] == "SKIP"


def _kit(tmp_path, *odbs):
    b = tmp_path / "kit/run/results/asap7/d/base"
    b.mkdir(parents=True)
    for o in odbs:
        (b / o).write_text("x")
    return tmp_path / "kit"


def test_eco_error_retry_seed(tmp_path):
    import signoff_chain as SC
    err = dict(verdict="ERROR", iterations=[{"n": 1}])
    assert SC.eco_error_retry(_kit(tmp_path, "5_1_grt.odb", "6_final.odb"), err) == "grt"
    assert SC.eco_error_retry(_kit(tmp_path / "b", "5_1_grt.odb", "5_2_route.odb"), err) == ""
    assert SC.eco_error_retry(_kit(tmp_path / "c", "5_1_grt.odb"), dict(verdict="EXHAUSTED", iterations=[{}])) is None
    assert SC.eco_error_retry(_kit(tmp_path / "d", "5_1_grt.odb"), dict(verdict="ERROR", iterations=[])) is None


def test_late_eco_retries_once(tmp_path):
    import signoff_chain as SC
    kit = _kit(tmp_path, "5_1_grt.odb", "6_final.odb")
    calls = []

    class Mod:
        @staticmethod
        def run_loop(kit, record, root=None, from_mode="", **kw):
            calls.append(from_mode)
            return dict(verdict="ERROR", reason="finish failed", iterations=[{"n": 1}], root=root)

        @staticmethod
        def summary(res):
            return res["verdict"]

    tool = tmp_path / "tools/die_plan/eco_loop.py"
    tool.parent.mkdir(parents=True)
    tool.write_text("import sys\nrun_loop = sys.modules['__nm_mod__'].run_loop\nsummary = sys.modules['__nm_mod__'].summary\n")
    sys.modules["__nm_mod__"] = Mod
    try:
        res = SC.late_eco(kit, kit / "signoff/signoff.json", None, 8, 2, current=lambda: (tool, "test"))
    finally:
        sys.modules.pop("__nm_mod__", None)
    assert calls == ["", "grt"]
    assert res["error_retry"]["from_mode"] == "grt"
