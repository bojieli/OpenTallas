"""KW-FIX-4 11-03: gen_hosts pick, spillable async PLACE argv default, restage of unstarted waiters"""
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as K


class FakeAP:
    DRY = False
    HUB_NAME = "intel2"
    def __init__(self):
        self.calls, self.logs = [], []
    def sh(self, argv, timeout=0):
        self.calls.append(argv); return 0, "", ""
    def log(self, m):
        self.logs.append(m)


def cfg(**d):
    base = {"gen_host": "intel1", "event": "e1", "plan": "/p", "src": "/s"}
    base.update(d)
    return {"dies": {"s81": base}}


ST = {"intel1": {"admit": 10, "load": 300, "cores": 256, "run": 9}, "epyc4": {"admit": 676, "load": 5, "cores": 256, "run": 0}}


def test_pick_default_unchanged():
    c = cfg(); c["_otrun_status"] = dict(ST)
    assert K.pick_gen_host(c, "s81") == "intel1"


def test_pick_most_admits_and_spreads():
    c = cfg(gen_hosts=["intel1", "epyc4"]); c["_otrun_status"] = {h: dict(v) for h, v in ST.items()}
    picks = [K.pick_gen_host(c, "s81", take=48) for _ in range(14)]
    assert picks[0] == "epyc4" and picks.count("epyc4") == 14 - picks.count("intel1")
    c2 = cfg(gen_hosts=["intel1", "epyc4"])               # no status -> configured gen host
    assert K.pick_gen_host(c2, "s81") == "intel1"


def _rec(tmp, g, argv=None, admitted=False):
    d = tmp / f"a_{g}_{bool(argv)}_{admitted}"
    d.mkdir()
    (d / "spec.json").write_text(json.dumps({"gen_host": g}))
    if argv:
        (d / "place_service.json").write_text(json.dumps({"unit": "kwp-x", "launch": "launched", "argv": argv}))
    (d / "place.live.log").write_text("ot-run: -> intel1\n" + ("ot-heavy: admitted on intel1\n" if admitted else ""))
    return {"die": "s81", "status": "RUNNING", "unit": "kw-u", "dir": str(d), "attempt": 1, "item": "t1"}


def test_restage_multi_and_pinned(tmp_path, monkeypatch):
    monkeypatch.setattr(K, "stop_reason", lambda *a, **k: None)
    c = cfg(gen_hosts=["intel1", "epyc4"], place_mem_gb=48); c["_otrun_status"] = {h: dict(v) for h, v in ST.items()}
    st = {"items": {"a": _rec(tmp_path, "intel1"), "b": _rec(tmp_path, "intel1", admitted=True),
                    "c": _rec(tmp_path, "epyc4")}}
    ap, notes = FakeAP(), {}
    assert K.restage_waiters(ap, c, st, notes) == 1
    assert st["items"]["a"]["status"] == "RETRY-INFRA" and st["items"]["b"]["status"] == "RUNNING"
    assert st["items"]["c"]["status"] == "RUNNING"
    assert ["systemctl", "--user", "stop", "kw-u"] in ap.calls
    assert K.infra_relaunch_due(c, st["items"]["a"])
    # KW-FIX-27: the move binds the relaunch, whatever spec_for reselected
    assert st["items"]["a"]["restage_host"] == "epyc4"
    sp = {"gen_host": "intel1"}
    K.bind_restage(c, "s81", st["items"]["a"], sp)
    assert sp["gen_host"] == "epyc4" and "restage_host" not in st["items"]["a"]
    sp = {"gen_host": "intel1"}
    K.bind_restage(c, "s81", {"restage_host": "gone"}, sp)
    assert sp["gen_host"] == "intel1"
    # pinned async PLACE waiter of a single-gen-host die
    c3 = cfg(place_mem_gb=48)
    d = tmp_path / "pin"; d.mkdir()
    (d / "spec.json").write_text(json.dumps({"gen_host": "intel2"}))
    (d / "place_service.json").write_text(json.dumps({"unit": "kwp-y", "launch": "launched", "argv": ["ot-run", "--hosts", "localhost"]}))
    (d / "place.live.log").write_text("ot-run: -> localhost (will queue)\n")
    st3 = {"items": {"p": {"die": "s81", "status": "RUNNING", "unit": "kw-p", "dir": str(d), "attempt": 1, "item": "t2"}}}
    ap3 = FakeAP()
    assert K.restage_waiters(ap3, c3, st3, {}) == 1
    assert ["systemctl", "--user", "stop", "kwp-y"] in ap3.calls
    c3["dies"]["s81"]["place_spill"] = False
    st3["items"]["p"]["status"] = "RUNNING"
    assert K.restage_waiters(FakeAP(), c3, st3, {}) == 0


def test_restage_spent_budget_is_infra_move(tmp_path, monkeypatch):
    # COORD 12:1x FLEET: a never-admitted waiter moves even with its infra budget used; the move is not charged
    monkeypatch.setattr(K, "stop_reason", lambda *a, **k: None)
    c = cfg(gen_hosts=["intel1", "epyc4"], place_mem_gb=48); c["_otrun_status"] = {h: dict(v) for h, v in ST.items()}
    r = _rec(tmp_path, "intel1"); r["attempt"] = 9
    st = {"items": {"a": r}}
    assert K.restage_waiters(FakeAP(), c, st, {}) == 1 and r["status"] == "RETRY-INFRA"
    assert K.infra_relaunch_due(c, r)
    a = tmp_path / "b"; a.mkdir()
    r2 = _rec(a, "intel1"); r2["attempt"], r2["infra_base"] = 2, 1          # budget left: base +1, not charged
    c["_otrun_status"] = {h: dict(v) for h, v in ST.items()}
    assert K.restage_waiters(FakeAP(), c, {"items": {"b": r2}}, {}) == 1 and r2["infra_base"] == 2
    assert (r2["attempt"] + 1) - r2["infra_base"] == 1                       # relaunch keeps infra_used 1


STW = {"epyc4": {"admit": 100, "load": 83, "cores": 256, "run": 56, "wait_n": 131, "wait_gb": 1359},
       "intel1": {"admit": 151, "load": 106, "cores": 112, "run": 45},      # busy, still taken (NO LOAD HOLD)
       "localhost": {"admit": 183, "load": 117, "cores": 112, "run": 62, "wait_n": 93, "wait_gb": 797}}


def test_score_counts_waiters():
    assert K.host_score(STW["epyc4"]) == 100 - 1359
    assert K.host_score(STW["intel1"]) > K.host_score(STW["localhost"]) > K.host_score(STW["epyc4"])
    c = cfg(gen_hosts=["epyc4", "intel1", "intel2"]); c["_hub"] = "intel2"
    c["_otrun_status"] = {h: dict(v) for h, v in STW.items()}
    assert K.pick_gen_host(c, "s81") == "intel1"


def test_restage_balances_waiters(tmp_path, monkeypatch):
    monkeypatch.setattr(K, "stop_reason", lambda *a, **k: None)
    c = cfg(gen_host="epyc4", gen_hosts=["epyc4", "intel1", "intel2"], place_mem_gb=10)
    c["_hub"], c["_otrun_status"], c["restage_max_per_tick"] = "intel2", {h: dict(v) for h, v in STW.items()}, 200
    items = {}
    for k in range(131):
        d = tmp_path / f"w{k}"; d.mkdir()
        (d / "spec.json").write_text(json.dumps({"gen_host": "epyc4"}))
        (d / "place.live.log").write_text("ot-run: -> epyc4 (will queue)\n")
        items[str(k)] = {"die": "s81", "status": "RUNNING", "unit": f"kw-{k}", "dir": str(d), "attempt": 4,
                         "infra_base": 0, "item": f"t{k}"}
    n = K.restage_waiters(FakeAP(), c, {"items": items}, {})
    s = c["_otrun_status"]
    assert n >= 60 and s["epyc4"]["wait_n"] <= 131 - 60 and s["intel1"]["wait_n"] > 0
    # balanced: epyc4 ends within one move of the best other host (localhost's own waiters have no records here)
    assert max(K.host_score(s[h]) for h in ("intel1", "localhost")) - K.host_score(s["epyc4"]) < 10
    # the moved records relaunch; the never-moved remain RUNNING
    assert sum(1 for r in items.values() if r["status"] == "RETRY-INFRA") == n


def test_spec_place_spill_default_and_epyc4_host():
    c = cfg(); c["dies"]["s81"]["hosts"] = None
    c["dies"]["s81"].pop("hosts")
    sp = K.spec_for(c, "s81", "t1", "intel2")
    assert sp["place_spill"] is True and "epyc4" in sp["hosts"] and sp["gen_host"] == "intel1"
    c["dies"]["s81"]["place_spill"] = False
    assert K.spec_for(c, "s81", "t1", "intel2")["place_spill"] is False


def test_place_async_argv_source():
    src = Path(K.__file__).read_text()
    i = src.index("def place_async(K, prun, m, t):")
    body = src[i:i + 2500]
    assert '"--stage", K, "--stage", prun' in body and 'otrun(m, t, K, cmd, [G])' in body


PS = """  100     1 bash -c export OT_SCRATCH=x; /usr/local/bin/ot-heavy --mem 10 --tag otrun-hub-1-11 -- bash -c cd /s/kit-wave/s81/items/a; echo
  101   100 /bin/bash /usr/local/bin/ot-heavy --mem 10 --tag otrun-hub-1-11 -- bash -c cd /s/kit-wave/s81/items/a
  102   101 flock 8
  200     1 /bin/bash /usr/local/bin/ot-heavy --mem 48 --tag otrun-hub-2-22 -- bash /s/kit-wave/s81/items/b/run.sh
  201   200 /usr/local/lib/ot-heavy/ot-heavy-exit oth-x bash /s/kit-wave/s81/items/b/run.sh
  300     1 /bin/bash /usr/local/bin/ot-heavy --mem 48 --tag otrun-hub-3-33 -- bash /s/kit-wave/s81/items/c/run.sh
  400     1 /bin/bash /usr/local/bin/ot-heavy --mem 48 --tag otrun-hub-4-44 -- bash /s/other-lane/x.sh
  500     1 /bin/bash /usr/local/bin/ot-heavy --mem 48 --tag otrun-otherhub-5-55 -- bash /s/kit-wave/x.sh
"""


def test_orphan_waiters():
    o = K.orphan_waiters(PS, "hub", live_pids={3})
    # 1: dead client, waiting -> both tagged pids; 2: started; 3: client alive; 4: not kit-wave; 5: other hub
    assert o == {"otrun-hub-1-11": [100, 101]}
    assert K.orphan_waiters(PS, "hub", live_pids={1, 3}) == {}


def test_spill_marked_host_is_no_gen_host():
    """COORD 14:2x INFRA class 2: an ot-run SPILL marker on the die lane root of a gen host -> ot-run NODIR for every
    attempt dir there; gen_hosts drops that host (the configured gen_host too while another stays), other dies keep it"""
    cfg = {"work_root": "/srv/opentallas-scratch2/claude/kit-wave",
           "dies": {"s81_head": {"gen_host": "intel2", "gen_hosts": ["epyc4", "intel2"],
                                 "work_root": "/srv/opentallas-scratch2/claude/codex-head-wave-1131/kit-wave"},
                    "hbm": {"gen_host": "intel2", "gen_hosts": ["intel2", "epyc4"]}}}
    assert K.gen_hosts(cfg, "s81_head") == ["epyc4", "intel2"]
    cfg["_spill_marked"] = {"epyc4": {"/srv/opentallas-scratch2/claude/codex-head-wave-1131"}}
    assert K.gen_hosts(cfg, "s81_head") == ["intel2"]
    assert K.gen_hosts(cfg, "hbm") == ["intel2", "epyc4"]
    cfg["_spill_marked"] = {"intel2": {"/srv/opentallas-scratch2/claude/codex-head-wave-1131"}}
    assert K.gen_hosts(cfg, "s81_head") == ["epyc4"]                    # KW-FIX-8: the configured gen_host leaves while another stays
    cfg["_spill_marked"] = {h: {"/srv/opentallas-scratch2/claude/codex-head-wave-1131"} for h in ("epyc4", "intel2")}
    assert K.gen_hosts(cfg, "s81_head") == ["intel2"]                   # none left: configured host, work_root_problem() says why


def test_spill_marked_probe():
    calls = []

    class AP:
        @staticmethod
        def sh(cmd, timeout=0):
            calls.append(cmd)
            return 0, "/srv/opentallas-scratch2/claude/codex-head-wave-1131\n", ""
    cfg = {"_hub": "intel2", "work_root": "/srv/opentallas-scratch2/claude/kit-wave",
           "dies": {"s81_head": {"gen_host": "intel2", "gen_hosts": ["epyc4", "intel2"],
                                 "work_root": "/srv/opentallas-scratch2/claude/codex-head-wave-1131/kit-wave"},
                    "hbm": {"gen_host": "intel2", "gen_hosts": ["intel2", "epyc4"]}}}
    got = K.spill_marked(AP, cfg)
    assert got == {"epyc4": {"/srv/opentallas-scratch2/claude/codex-head-wave-1131"}}
    assert len(calls) == 1 and calls[0][-2] == "epyc4" and ".ot-run-spill-copy" in calls[0][-1]
    assert K.lane_root("/srv/opentallas-scratch2/claude/kit-wave/hbm/d44v") == "/srv/opentallas-scratch2/claude/kit-wave"


def test_item_env():
    """item_env: per-item gen environment (DIE-HEAD-58 hd_mesh_e OT_IO_HOLD=sender_min), validated"""
    d = {"item_env": {"hd_mesh_e": {"OT_IO_HOLD": "sender_min"}}}
    assert K.item_env(d, "hd_mesh_e") == {"OT_IO_HOLD": "sender_min"}
    assert K.item_env(d, "hd_mesh") == {}
    import pytest
    with pytest.raises(ValueError):
        K.item_env({"item_env": {"x": {"PATH": "/tmp"}}}, "x")
    with pytest.raises(ValueError):
        K.item_env({"item_env": {"x": {"OT_A": "a; rm -rf /"}}}, "x")


def test_place_service_asks_for_the_spill_handoff():
    # SPILL-PROOF-1: an old ot-run ignores the variable, so ot-run and kit_wave deploy in either order
    src = (Path(__file__).parent / "kit_wave.py").read_text()
    assert "--setenv=OT_RUN_SPILL_HANDOFF=place" in src


# KW-FIX-24 11-06 (COORD 16:2x): epyc6 scratch2 44 GB -> new and restaged attempts go to intel1/intel2
SDISK = ("ot-run status: epyc6 admits 300 GB (avail 400, reserve 0, fresh 0, peak 30) load 10/128 run 3 root 87% "
         "scratch 44 GB | intel1 admits 100 GB (avail 390, reserve 0, fresh 0, peak 46.8) load 104/112 run 50 root 62% "
         "scratch 191 GB | localhost admits 90 GB (avail 517, reserve 0, fresh 0, peak 59.8) load 89/112 run 33 "
         "root 70% scratch 212 GB | epyc5 REFUSED (scratch disk /srv/opentallas-scratch has 34 GB free < floor 50 GB)")


def test_gen_disk_low_parsed_and_ranked_last():
    s = K.parse_otrun_status(SDISK)
    assert s["epyc6"]["scratch_gb"] == 44 and s["intel1"]["scratch_gb"] == 191 and "epyc5" not in s
    assert K.gen_disk_low(s["epyc6"]) and not K.gen_disk_low(s["intel1"]) and not K.gen_disk_low({"admit": 5})
    assert not K.gen_disk_low(s["epyc6"], floor=0) and not K.gen_disk_low(s["epyc6"], floor=40)
    assert K.host_score(s["epyc6"]) < min(K.host_score(s["localhost"]), K.host_score(s["intel1"]))
    assert K.host_score(s["epyc6"]) > K.host_score(None)            # REFUSED / absent stays lowest
    c = cfg(gen_host="epyc6", gen_hosts=["epyc6", "intel1", "intel2"]); c["_hub"] = "intel2"
    c["_otrun_status"] = s
    assert K.pick_gen_host(c, "s81") == "intel2"                    # localhost row = the hub; intel1 is busy
    c1 = cfg(gen_host="epyc6", gen_hosts=["epyc6", "epyc5"]); c1["_otrun_status"] = s
    assert K.pick_gen_host(c1, "s81") == "epyc6"                    # nothing better: unchanged


def test_restage_moves_waiters_off_low_disk_host(tmp_path, monkeypatch):
    monkeypatch.setattr(K, "stop_reason", lambda *a, **k: None)
    c = cfg(gen_host="epyc6", gen_hosts=["epyc6", "intel1", "intel2"], place_mem_gb=10)
    c["_hub"], c["_otrun_status"] = "intel2", K.parse_otrun_status(SDISK)
    items = {}
    for k in range(3):
        d = tmp_path / f"w{k}"; d.mkdir()
        (d / "spec.json").write_text(json.dumps({"gen_host": "epyc6"}))
        (d / "place.live.log").write_text("ot-run: -> epyc6 (will queue)\n")
        items[str(k)] = {"die": "s81", "status": "RUNNING", "unit": f"kw-{k}", "dir": str(d), "attempt": 2,
                         "infra_base": 0, "item": f"t{k}"}
    ap = FakeAP()
    assert K.restage_waiters(ap, c, {"items": items}, {}) == 3
    assert all(r["status"] == "RETRY-INFRA" and "epyc6 -> " in r["reason"] for r in items.values())


def test_restage_young_waiter_stays(tmp_path, monkeypatch):
    # KW-FIX-24: a waiter launched < restage_min_wait_s ago is not moved (ping-pong); an old one is
    monkeypatch.setattr(K, "stop_reason", lambda *a, **k: None)
    c = cfg(gen_hosts=["intel1", "epyc4"], place_mem_gb=48); c["_otrun_status"] = {h: dict(v) for h, v in ST.items()}
    young = _rec(tmp_path, "intel1"); young["started"] = time.time() - 600
    st = {"items": {"y": young}}
    assert K.restage_waiters(FakeAP(), c, st, {}) == 0 and young["status"] == "RUNNING"
    young["started"] = time.time() - 2400
    assert K.restage_waiters(FakeAP(), c, st, {}) == 1 and young["status"] == "RETRY-INFRA"
    c["restage_min_wait_s"] = 0
    y2 = dict(young, status="RUNNING", started=time.time())
    assert K.restage_waiters(FakeAP(), c, {"items": {"y": y2}}, {}) == 1


def test_restage_wait_doubles_per_move(tmp_path, monkeypatch):
    monkeypatch.setattr(K, "stop_reason", lambda *a, **k: None)
    c = cfg(gen_hosts=["intel1", "epyc4"], place_mem_gb=48); c["_otrun_status"] = {h: dict(v) for h, v in ST.items()}
    r = _rec(tmp_path, "intel1"); r["started"] = time.time() - 2400; r["restage_n"] = 1
    st = {"items": {"y": r}}
    assert K.restage_waiters(FakeAP(), c, st, {}) == 0 and r["status"] == "RUNNING"    # 40 min < 60 min after one move
    r["started"] = time.time() - 3700
    assert K.restage_waiters(FakeAP(), c, st, {}) == 1 and r["restage_n"] == 2
    r2 = dict(r, status="RUNNING", started=time.time() - 3 * 3600, restage_n=9)        # the cap is x8 = 4 h
    assert K.restage_waiters(FakeAP(), c, {"items": {"y": r2}}, {}) == 0
    r2["started"] = time.time() - 4 * 3600 - 60
    assert K.restage_waiters(FakeAP(), c, {"items": {"y": r2}}, {}) == 1


def test_counted_now_follows_counter_and_plan_block(tmp_path):
    p = tmp_path / "cache.json"
    p.write_text(json.dumps({"plans": {"x": {"die": "s81", "signed_types": {"t1": []}, "signed_designs": {"c1": []}}}}))
    c = cfg(); c["counter_cache"] = str(p); K.load_counter_signed(c); st = {}
    assert K.counted_now(c, st, "s81", "t1", "b1") and K.counted_now(c, st, "s81", "c1")
    assert not K.counted_now(c, st, "s81", "other", "b1") and not K.counted_now(c, st, "hbm", "t1", "b1")
    assert K.counted_now(c, st, "s81", "t1", "b1") and not K.counted_now(c, st, "s81", "t1", "b2")   # the plan changed it
    c["dies"]["s81"]["rebuild_counted"] = ["c1"]
    assert not K.counted_now(c, st, "s81", "c1")
    c2 = cfg(); c2["counter_cache"] = str(tmp_path / "absent.json"); K.load_counter_signed(c2)
    assert not K.counted_now(c2, {}, "s81", "t1", "b1")                  # no cache: as before


def test_restage_stops_counted_waiter_without_moving_it(tmp_path, monkeypatch):
    monkeypatch.setattr(K, "stop_reason", lambda *a, **k: None)
    c = cfg(gen_hosts=["intel1", "epyc4"], place_mem_gb=48); c["_otrun_status"] = {h: dict(v) for h, v in ST.items()}
    r = _rec(tmp_path, "intel1"); r["started"] = time.time() - 60
    c["_counter_signed"] = {r["die"]: {r["item"]}}
    assert K.restage_waiters(FakeAP(), c, {"items": {"y": r}}, {}) == 1
    assert r["status"] == "RETRY-INFRA" and r["restage_host"] == "intel1" and "counted" in r["reason"]


# ------------------------------------------------------------------------------------------------ SCHED-1 11-07 load hold
STL = {"epyc2": {"admit": 164, "load": 212, "cores": 128, "run": 68, "wait_n": 76, "wait_gb": 2900, "scratch_gb": 157},
       "intel1": {"admit": 200, "load": 120, "cores": 112, "run": 60, "scratch_gb": 348},
       "epyc5": {"admit": 300, "load": 62, "cores": 128, "run": 45, "scratch_gb": 63},
       "epyc6": {"admit": 300, "load": 50, "cores": 128, "run": 36, "scratch_gb": 40}}


def _loadcfg(hosts, **kw):
    c = cfg(gen_host=hosts[0], gen_hosts=hosts, **kw)
    c["_otrun_status"] = {h: dict(v) for h, v in STL.items()}
    return c


def test_over_cap_is_the_ot_heavy_rule():
    assert K.over_load_cap({"load": 192, "cores": 128}) and K.over_load_cap({"load": 192.9, "cores": 128})
    assert not K.over_load_cap({"load": 191.9, "cores": 128}) and not K.over_load_cap({"load": 900})
    assert not K.host_room(None) and not K.host_room(dict(STL["epyc6"])) and K.host_room(dict(STL["epyc5"]))


def test_hold_only_when_no_gen_host_has_room():
    assert K.load_hold(_loadcfg(["epyc2"]), "s81").startswith("LOAD-HOLD")
    assert K.load_hold(_loadcfg(["epyc2", "epyc6"]), "s81").startswith("LOAD-HOLD")   # epyc6 is under the disk floor
    assert K.load_hold(_loadcfg(["epyc2", "intel1"]), "s81") == ""
    c = cfg(gen_host="epyc2", gen_hosts=["epyc2"])                                    # no status: unchanged
    assert K.load_hold(c, "s81") == ""
    c = _loadcfg(["epyc2"]); c["load_hold"] = False
    assert K.load_hold(c, "s81") == ""
    c = _loadcfg(["epyc2"]); c["_near_count"] = {("s81", "a")}                        # launches --crit: no hold
    assert K.load_hold(c, "s81", "a") == "" and K.load_hold(c, "s81", "b") != ""


def test_pick_least_loaded_host_with_room():
    assert K.pick_gen_host(_loadcfg(["epyc2", "intel1", "epyc5"]), "s81", take=48) == "epyc5"
    assert K.pick_gen_host(_loadcfg(["epyc2", "intel1"]), "s81", take=48) == "intel1"
    assert K.pick_gen_host(_loadcfg(["epyc2", "epyc6"]), "s81") == "epyc2"            # no room anywhere: old score order


def test_burst_stops_at_cap():
    c = _loadcfg(["epyc2", "intel1"])
    n = 0
    while not K.load_hold(c, "s81") and n < 50:
        assert K.pick_gen_host(c, "s81", take=48, threads=8) == "intel1"
        n += 1
    assert n == 6                                                                      # 120 + 6 x 8 = 168 = 1.5 x 112


def test_order_unlocks_blocked_parents_first():
    d = {"_prov_deps": {"p1": ["m_b", "m_a"], "p2": ["m_b"], "p3": ["m_b", "m_c"]}}
    assert K.blocked_parents(d) == {"m_b": 3, "m_a": 1, "m_c": 1}
    assert K.blocked_parents({"_plan_deps": {"p": ["x"]}}) == {"x": 1} and K.blocked_parents({}) == {}
    rows = [dict(die="s81", item=i, kind="core", state="NEEDS-KIT", owner="KIT-WAVE", live_job="none", last_activity="",
                 replicas=r) for i, r in (("m_a", "9"), ("m_b", "1"), ("m_c", "2"))]
    c = {"dies": {"s81": dict(d, event="e1", plan="/p", src="/s", gen_host="epyc5", pilot_gate=False, kinds=["core", "type"])}}
    picked, _ = K.select(rows, c, "s81", {"items": {}})
    assert [r["item"] for r in picked] == ["m_b", "m_a", "m_c"]


def _failrec(tmp_path, cfgd, **over):
    d = tmp_path / "a1"; d.mkdir()
    (d / "spec.json").write_text(json.dumps(K.spec_for(dict(cfgd, _otrun_status={}), "s81", "t1", "")))
    return dict({"die": "s81", "item": "t1", "attempt": 1, "status": "FAIL", "class": "TIMING", "dir": str(d)}, **over)


def test_unchanged_fail_holds_same_inputs_only(tmp_path):
    c = cfg(); r = _failrec(tmp_path, c, **{"class": "FLOW"})
    assert K.unchanged_fail(c, {}, "s81", "t1", r)                                    # same inputs
    assert not K.unchanged_fail(c, {}, "s81", "t1", dict(r, **{"class": "INFRA"}))     # an infra failure is not a design retry
    assert not K.unchanged_fail(c, {}, "s81", "t1", dict(r, status="CANCELLED"))
    assert not K.unchanged_fail(c, {}, "s81", "t1", dict(r, dir=str(tmp_path / "gone")))
    assert not K.unchanged_fail(c, {"leafslew": {"k": {"die": "s81", "item": "t1", "attempt": 1}}}, "s81", "t1", r)
    c2 = cfg(); c2["dies"]["s81"]["src_sha"] = "new"                                    # new source
    assert not K.unchanged_fail(c2, {}, "s81", "t1", r)
    c3 = cfg(); c3["dies"]["s81"]["gen_args"] = ["--form", "x"]                         # new arguments
    assert not K.unchanged_fail(c3, {}, "s81", "t1", r)
    c4 = cfg(); c4["dies"]["s81"]["_prov_keys"] = {"t1": "views2"}                      # new child views
    assert not K.unchanged_fail(c4, {}, "s81", "t1", dict(r, prov_key="views1"))
    c5 = cfg(gen_hosts=["epyc4"], place_mem_gb=999)                                     # where it runs is no input
    assert K.unchanged_fail(c5, {}, "s81", "t1", r)


def test_timing_or_routing_fail_needs_a_named_redesign(tmp_path):
    c = cfg(); r = _failrec(tmp_path, c, status="ENQUEUED", q_status="FAIL", q_class="ROUTING")
    c["dies"]["s81"]["src_sha"] = "new"
    assert K.unchanged_fail(c, {}, "s81", "t1", r)                                      # a new source alone is no change
    c["dies"]["s81"]["retry_fix"] = {"t1@1": "class batch, new flow tag"}
    assert K.unchanged_fail(c, {}, "s81", "t1", r)
    c["dies"]["s81"]["retry_fix"] = {"t1@1": "REDESIGN: +1 pin cycle on u_k_off"}
    assert not K.unchanged_fail(c, {}, "s81", "t1", r)
    c2 = cfg(); c2["dies"]["s81"]["gen_args"] = ["--form", "x"]                           # a changed flag is not named
    assert K.unchanged_fail(c2, {}, "s81", "t1", r)
    assert not K.unchanged_fail(c, {}, "s81", "t1", dict(r, q_class="INFRA"))
