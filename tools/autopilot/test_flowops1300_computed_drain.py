"""FLOW-OPS-1300 / FABLE-FLOW-1900: the drain is computed (scratch free < floor + margin) in host_drain, the one admission function of ot-run and the wave;
the wave holds a die whose every gen host drains (load_hold false or not) and a tick's burst charges each gen's disk to the cached figure."""
import importlib.util, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "fleet"))
import host_drain as HD  # noqa: E402

sp = importlib.util.spec_from_file_location("kit_wave_cd", HERE / "kit_wave.py")
KW = importlib.util.module_from_spec(sp)
sp.loader.exec_module(KW)


def test_computed_cap_and_admit(monkeypatch):
    for k in ("OT_RUN_SCRATCH_DISK_FLOOR_GB", "OT_RUN_SCRATCH_DISK_FLOOR_GB_HOSTS", "OT_DRAIN_COMPUTED"):
        monkeypatch.delenv(k, raising=False)
    assert HD.cap_of({}, "epyc10") == 50 + HD.DRAIN_MARGIN_GB
    assert HD.cap_of({"epyc10": 9999}, "epyc10") == 9999                       # a hand cap still raises it
    assert HD.cap_of({}, "epyc10", computed=False) == 0
    assert HD.draining({}, {"epyc10": 35, "epyc7": 162, "epyc8": None}) == {"epyc10": (35, 90)}
    ok, why = HD.admit("epyc10", 72, caps={})
    assert ok is False and "DRAINING" in why and "floor 50" in why
    assert HD.admit("epyc7", 162, caps={}) == (True, "")
    assert HD.admit("epyc7", 100, need_gb=20, caps={})[0] is False
    assert HD.admit("epyc7", None, caps={}) == (True, "")
    monkeypatch.setenv("OT_RUN_SCRATCH_DISK_FLOOR_GB_HOSTS", "epyc2=140")
    assert HD.cap_of({}, "epyc2") == 140 + HD.DRAIN_MARGIN_GB
    monkeypatch.setenv("OT_RUN_SCRATCH_DISK_FLOOR_GB", "10")
    assert HD.floor_of("epyc9") == 50                                          # never under the hard floor
    monkeypatch.setenv("OT_DRAIN_COMPUTED", "0")
    assert HD.cap_of({}, "epyc10") == 0


def _cfg(free):
    stt = {h: dict(scratch_gb=f, load=1, cores=96, admit_gb=500, wait_n=0) for h, f in free.items()}
    return {"dies": {"qwen_compute": {"gen_host": "epyc10", "gen_hosts": list(free)}}, "_otrun_status": stt, "_hub": "intel2", "load_hold": False}


def test_wave_holds_when_every_gen_host_drains(monkeypatch):
    monkeypatch.setattr(HD, "load_caps", lambda now=None, fetch=None: {})
    monkeypatch.setattr(KW, "_host_drain", lambda: HD)
    c = _cfg({"epyc10": 35, "epyc8": 60})
    r = KW.load_hold(c, "qwen_compute", "cbf_q00")
    assert r.startswith("DRAIN-HOLD") and "epyc10 35 GB" in r
    c = _cfg({"epyc10": 35, "epyc8": 300})
    assert KW.load_hold(c, "qwen_compute", "cbf_q00") == ""                    # one host with room: no hold (load_hold false)
    assert KW.gen_hosts(c, "qwen_compute") == ["epyc8"]                        # the drained host is no gen host


def test_burst_charges_disk_until_drain(monkeypatch):
    monkeypatch.setattr(HD, "load_caps", lambda now=None, fetch=None: {})
    monkeypatch.setattr(KW, "_host_drain", lambda: HD)
    c = _cfg({"epyc10": 98, "epyc8": 400})
    c["gen_disk_charge_gb"] = 4
    st = c["_otrun_status"]
    before = st["epyc10"]["scratch_gb"] + st["epyc8"]["scratch_gb"]
    for _ in range(5):
        KW.pick_gen_host(c, "qwen_compute", take=1)
    assert st["epyc10"]["scratch_gb"] + st["epyc8"]["scratch_gb"] == before - 20
    assert "epyc10" not in KW.gen_hosts(c, "qwen_compute") or st["epyc10"]["scratch_gb"] >= 90
