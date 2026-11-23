"""HARD-PIN-1122 (COORD 11-22): a --hosts pin never falls back or spills off its hosts; a transient refusal waits there.
SLWSLE sle_su_l1 geom (PIN-FALLBACK epyc8 -> epyc2, no kit dir) and QC-COLL-R3 LEC r4 (PIN-SPILL epyc10 -> epyc2) both died rc 127."""
import importlib.machinery, importlib.util, pathlib
H = pathlib.Path(__file__).parent
l = importlib.machinery.SourceFileLoader("ot_run_hardpin", str(H / "ot-run"))
RUN = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_run_hardpin", l)); l.exec_module(RUN)

LEC = ["--mem", "96", "--threads", "8", "--hosts", "epyc10", "--dir", "/srv/s", "--stage", "/srv/s", "--stage", "/srv/k", "--", "bash", "/srv/s/lec_rerun.sh"]


def test_no_pin_fallback_by_default(monkeypatch):
    for k in ("OT_RUN_SOFT_PIN", "OT_RUN_STRICT_HOST", "OT_RUN_HARD_PIN"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(RUN, "PIN_FALLBACK", [False])
    assert RUN.pin_fallback_pool(["epyc8"], {}, ["bash", "geom_check.sh"], pool=["epyc2", "epyc8", "intel1"]) is None
    assert RUN.PIN_FALLBACK == [False]


def test_no_pin_spill_by_default():
    assert RUN.pin_spill_args(LEC, RUN.PIN_SPILL_AFTER_S + 10, ["epyc2", "epyc10"], env={}) is LEC


def test_soft_pin_restores_old_behaviour(monkeypatch):
    monkeypatch.setenv("OT_RUN_SOFT_PIN", "1")
    monkeypatch.delenv("OT_RUN_STRICT_HOST", raising=False)
    monkeypatch.setattr(RUN, "PIN_FALLBACK", [False])
    assert RUN.pin_fallback_pool(["epyc8"], {}, ["true"], pool=["epyc2", "epyc8"]) == ["epyc8", "epyc2"]
    a = RUN.pin_spill_args(LEC, RUN.PIN_SPILL_AFTER_S + 10, ["epyc2", "epyc10"], env={"OT_RUN_SOFT_PIN": "1"})
    assert a[a.index("--hosts") + 1] == "epyc10,epyc2"


def test_pin_wait_on_transient_refusal(monkeypatch):
    monkeypatch.delenv("OT_RUN_SOFT_PIN", raising=False)
    # epyc8 holds the kit dir but is under its scratch floor: wait there
    assert RUN.pin_wait(True, False, ["epyc8"], [], None, 5000)
    assert RUN.pin_wait(True, False, ["epyc8"], [], 600, 100)
    assert not RUN.pin_wait(True, False, ["epyc8"], [], 600, 700)          # --max-wait is kept
    assert not RUN.pin_wait(True, False, ["epyc8"], ["epyc8"], None, 0)    # the dir is missing there: SETUP NOT RUN, not a wait
    assert not RUN.pin_wait(False, False, ["epyc8"], [], None, 0)          # unpinned jobs keep their spill / NOT RUN path
    assert not RUN.pin_wait(True, True, ["epyc8"], [], None, 0)            # --pick answers now
    monkeypatch.setenv("OT_RUN_SOFT_PIN", "1")
    assert not RUN.pin_wait(True, False, ["epyc8"], [], None, 0)


def test_main_wiring():
    src = (H / "ot-run").read_text()
    i = src.index("if pin_wait(_pinned_req is not None, pick, hosts, _nod")
    assert i < src.index('_pf = f"SETUP: --dir {d} exists on none of the candidate hosts')
    assert "and soft_pin():   # HARD-PIN-1122" in src


def test_pinned_disk_floor_waits_on_the_pin_and_never_runs_elsewhere():
    """SLWSLE shape end to end: --hosts epyc8 --dir K, epyc8 refused by its scratch floor, epyc2 free: the client waits (sleeps), runs nowhere"""
    import sys
    sys.path.insert(0, str(H))
    from test_ot_run_load_hold import exercise, load, row
    m = load(H / "ot-run")
    rows = dict(epyc8={**row(200, 10, 96), "disk_refusal": "scratch disk /srv/opentallas-scratch has 99 GB free < floor 100 GB"},
                epyc2={**row(400, 10, 128)})
    r = exercise(m, rows, extra=("--hosts", "epyc8", "--dir", "/srv/k"), mem=24)
    assert r["held"] and r["host"] is None, r
    assert "PIN-WAIT" in r["log"] and "PIN-FALLBACK" not in r["log"], r["log"]
