"""WAVE-DISK-CAP 11-17 (COORD, FLEET-OPS-R 4db4880): per-item --disk, launch refusal on in-flight disk, terminal reclaim sweep, place_prefer skips falling hosts."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW


def cfg(peak=20.0, **d):
    die = {"gen_hosts": ["h1", "h2"], "gen_host": "h1"}
    die.update(d)
    return {"dies": {"s": die}, "_gen_peak_gb": peak,
            "_otrun_status": {"h1": {"scratch_gb": 400}, "h2": {"scratch_gb": 400}}}


def test_item_disk_is_max_of_peak_and_three_times_replicas_capped():
    assert KW.item_disk_gb(cfg(20.0), "s", "i", 1) == 20
    assert KW.item_disk_gb(cfg(1.2), "s", "i", 1) == 3
    assert KW.item_disk_gb(cfg(None), "s", "i", 1) == 3
    assert KW.item_disk_gb(cfg(20.0), "s", "i", 60) == 20
    assert KW.item_disk_gb(cfg(20.0, disk_replicas_max=4), "s", "i", 60) == 80
    assert KW.item_disk_gb(cfg(20.0, item_disk_gb={"col_*": 7}), "s", "col_h9", 1) == 7
    assert KW.item_disk_gb(cfg(20.0, disk_cap=False), "s", "i", 1) == 0


def test_heavy_args_carry_the_disk_budget():
    assert KW.heavy_args({"item_disk_gb": 12})[-2:] == ["--disk", "12"]
    assert "--disk" not in KW.heavy_args({})


def test_launch_refused_when_in_flight_plus_new_exceeds_free_minus_150():
    c = cfg(20.0)
    st = {"items": {"a": {"die": "s", "status": "RUNNING", "gen_host": "h1", "item_disk_gb": 100},
                    "b": {"die": "s", "status": "FAIL", "gen_host": "h1", "item_disk_gb": 500},
                    "c": {"die": "s", "status": "ENQUEUED", "gen_host": "h2", "item_disk_gb": 100}}}
    assert KW.inflight_disk_gb(st, "h1") == 100
    assert KW.disk_cap_refusal(c, st, "s", 20) == ""                          # 100 + 20 <= 400 - 150
    c["_otrun_status"] = {"h1": {"scratch_gb": 260}, "h2": {"scratch_gb": 262}}
    why = KW.disk_cap_refusal(c, st, "s", 20)                                 # 120 > 110 and 120 > 112: no host fits
    assert why.startswith("disk cap:") and "h1" in why and "h2" in why
    c["_otrun_status"]["h2"]["scratch_gb"] = 300                              # h2: 120 <= 150: one host fits
    assert KW.disk_cap_refusal(c, st, "s", 20) == ""
    c["_otrun_status"] = {"h1": {}, "h2": {"scratch_gb": 1}}                  # no reading on a host: not a reason
    assert KW.disk_cap_refusal(c, st, "s", 20) == ""
    assert KW.disk_cap_refusal(dict(c, disk_cap=False), st, "s", 20) == ""


def test_launch_safe_waits_without_a_row_and_logs_once(monkeypatch):
    logs, launched = [], []

    class AP:
        DRY = False
        log = staticmethod(logs.append)
    monkeypatch.setattr(KW, "launch", lambda *a, **k: launched.append(1) or {"unit": "u"})
    monkeypatch.setattr(KW, "note_unblock_launch", lambda *a: None)
    c = cfg(20.0)
    c["_otrun_status"] = {"h1": {"scratch_gb": 160}, "h2": {"scratch_gb": 160}}
    st = {}
    assert KW.launch_safe(AP, c, st, "s", {"item": "i", "replicas": 1}, "hub") is None
    assert KW.launch_safe(AP, c, st, "s", {"item": "i", "replicas": 1}, "hub") is None
    assert not launched and len([m for m in logs if "LAUNCH-DISK-CAP" in m]) == 1
    c["_otrun_status"]["h1"]["scratch_gb"] = 400
    assert KW.launch_safe(AP, c, st, "s", {"item": "i", "replicas": 1}, "hub") == {"unit": "u"}


def test_place_prefer_skips_a_host_falling_faster_than_50_gb_h():
    stt = {"h1": {"admit": 100, "scratch_gb": 300}, "h2": {"admit": 100, "scratch_gb": 300}}
    assert KW.place_prefer_live(["h1", "h2"], stt, 16, fall={"h1": 80.0, "h2": 10.0}) == ["h2"]
    assert KW.place_prefer_live(["h1", "h2"], stt, 16, fall={"h1": 50.0}) == ["h1", "h2"]        # exactly 50 is allowed
    assert KW.place_prefer_live(["h1", "h2"], stt, 16) == ["h1", "h2"]


def test_terminal_sweep_reaps_failed_and_cancelled_once(monkeypatch):
    calls = []

    class AP:
        DRY = False
        log = staticmethod(lambda m: None)
    monkeypatch.setattr(KW, "grt_arm_reclaim", lambda ap, rec, hosts: calls.append(rec["item"]) or "ok")
    now = 10_000_000.0
    c = {"dies": {"s": {"gen_host": "h1"}}}
    row = lambda item, status, cls="", att=2, upd=now - 3600: {"die": "s", "item": item, "status": status, "class": cls, "attempt": att, "updated": upd}
    st = {"items": {"1": row("f", "FAIL", "FLOW"), "2": row("c", "CANCELLED", "SUPERSEDED"), "3": row("i", "FAIL", "INFRA"),
                    "4": row("a1", "FAIL", "FLOW", att=1), "5": row("fresh", "FAIL", "FLOW", upd=now - 10),
                    "6": row("live", "FAIL", "FLOW"), "7": {"die": "s", "item": "live", "status": "RUNNING"},
                    "8": row("old", "FAIL", "FLOW", upd=now - 90000)}}
    assert KW.reclaim_terminal_sweep(AP, c, st, now=now) == 2
    assert sorted(calls) == ["c", "f"]
    assert KW.reclaim_terminal_sweep(AP, c, st, now=now) == 0                 # each row once
    assert KW.reclaim_terminal_sweep(AP, dict(c, reclaim_failed=False), {"items": {"1": row("z", "FAIL", "FLOW")}}, now=now) == 0
