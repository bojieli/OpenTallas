"""FLEET-WATCH-R5 11-21 (FABLE-FLOW-0800 classes c, d): a plan apply cannot rewrite fleet keys or re-add a host under its admit cap; the gen pick skips hosts under their cap;
a pending apply holds new launches for the die (max 60 min)."""
import json
import time
import kit_wave as K
import apply_reviewed_tree_marker as A
import test_apply_reviewed_tree_marker as T


def test_apply_keeps_fleet_keys_and_does_not_readd_a_capped_host():
    c = T.mk({"gen_hosts": ["epyc10", "epyc2"], "gen_host": "epyc10", "gen_host_min_free_gb": {"epyc9": 250}, "restage_max_per_tick": 12})
    cand = dict(T.cand(), hosts=["epyc10", "epyc9"], config={"gen_host_min_free_gb": {}, "restage_max_per_tick": 99, "event": "E1"})
    r = T.apply(c, cand, "/x/old", "E0", pilot_item="t1", TC=T.TC, free_probe=lambda h: 169)
    d = json.loads((c / "autopilot/kit_wave.json").read_text())["dies"]["kv"]
    assert d["gen_host_min_free_gb"] == {"epyc9": 250} and d["restage_max_per_tick"] == 12
    assert "epyc9" not in d["gen_hosts"] and "epyc10" in d["gen_hosts"]
    assert any("APPLY-KEPT" in w for w in r.get("warnings", [])), r.get("warnings")


def test_apply_adds_the_host_once_it_clears_the_cap():
    c = T.mk({"gen_hosts": ["epyc10"], "gen_host": "epyc10", "gen_host_min_free_gb": {"epyc9": 250}})
    T.apply(c, dict(T.cand(), hosts=["epyc10", "epyc9"]), "/x/old", "E0", pilot_item="t1", TC=T.TC, free_probe=lambda h: 300)
    assert "epyc9" in json.loads((c / "autopilot/kit_wave.json").read_text())["dies"]["kv"]["gen_hosts"]


def test_apply_clears_event_pending():
    c = T.mk({"event_pending": {"event": "E1", "since": time.time()}})
    T.apply(c, T.cand(), "/x/old", "E0", pilot_item="t1", TC=T.TC)
    assert "event_pending" not in json.loads((c / "autopilot/kit_wave.json").read_text())["dies"]["kv"]


def test_gen_hosts_drops_a_host_under_its_cap():
    cfg = {"dies": {"s81": {"gen_host": "epyc8", "gen_hosts": ["epyc8", "intel1", "epyc9"], "gen_host_min_free_gb": {"intel1": 250, "epyc9": 250}, "work_root": "/srv/x/w"}},
           "_hub": "intel2", "_otrun_status": {"epyc8": {"scratch_gb": 400}, "intel1": {"scratch_gb": 120}, "epyc9": {"scratch_gb": 169}}}
    assert K.gen_hosts(cfg, "s81") == ["epyc8"]
    cfg["_otrun_status"]["intel1"]["scratch_gb"] = 300
    assert K.gen_hosts(cfg, "s81") == ["epyc8", "intel1"]
    cfg["_otrun_status"]["epyc8"]["scratch_gb"] = 10
    only = dict(cfg, dies={"s81": dict(cfg["dies"]["s81"], gen_hosts=["intel1", "epyc9"], gen_host="intel1")})
    assert K.gen_hosts(only, "s81") == ["intel1"]            # epyc9 (169 < 250) goes, intel1 (300) stays


def test_event_pending_holds_new_launches_for_that_die_only_and_expires():
    class AP:
        logs = []
        @classmethod
        def log(cls, m): cls.logs.append(m)
    now = time.time()
    cfg = {"dies": {"kv": {"event_pending": {"event": "E1", "since": now - 60}}, "s81": {}}}
    st = {}
    assert K.event_pending_wait(AP, cfg, st, "kv", now) is True
    assert K.event_pending_wait(AP, cfg, st, "kv", now) is True and len(AP.logs) == 1      # logged once
    assert K.event_pending_wait(AP, cfg, st, "s81", now) is False
    cfg["dies"]["kv"]["event_pending"]["since"] = now - 3700
    assert K.event_pending_wait(AP, cfg, st, "kv", now) is False and "expired" in AP.logs[-1]
