import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW

SRC = "/srv/s/kw45/src_kv_pin_x_d21b"


def die(**kw):
    d = {"src": SRC, "die_gen_env": {"OT_SIGNED_VIEW_SHA": SRC + "/physical/signed_view_sha_kv.json", "OT_N": "4"}}
    d.update(kw)
    return d


def test_in_tree_and_system_paths_pass_outside_paths_are_listed():
    assert KW.gen_env_outside_tree(die(), "i") == []
    d = die(die_gen_env={"OT_SIGNED_VIEW_SHA": "/srv/s/kit-ops-6/signed_view_sha_kv.json", "OT_X": "/work/a /OpenROAD-flow-scripts/b", "OT_N": "4"})
    assert KW.gen_env_outside_tree(d, "i") == [("OT_SIGNED_VIEW_SHA", "/srv/s/kit-ops-6/signed_view_sha_kv.json")]
    d["item_env"] = {"i": {"OT_Y": "x:/srv/s/other/f.json"}}                      # an item's own env counts for that item only
    assert [k for k, _ in KW.gen_env_outside_tree(d, "i")] == ["OT_SIGNED_VIEW_SHA", "OT_Y"]
    assert [k for k, _ in KW.gen_env_outside_tree(d, "j")] == ["OT_SIGNED_VIEW_SHA"]
    assert KW.gen_env_outside_tree(dict(SRC + "x" and d, src=SRC + "x"), "j")      # a sibling tree sharing the prefix is NOT the tree


def test_opt_out_and_allowlist():
    d = die(die_gen_env={"OT_A": "/srv/s/o/f", "OT_B": "/srv/s/o/g"})
    assert len(KW.gen_env_outside_tree(d, "i")) == 2
    assert [k for k, _ in KW.gen_env_outside_tree(dict(d, gen_env_outside_allow=["OT_A"]), "i")] == ["OT_B"]
    assert KW.gen_env_outside_tree(dict(d, gen_env_outside_ok=True), "i") == []


def test_launch_refuses_once_and_does_not_start(monkeypatch):
    logs = []

    class AP:
        DRY = False
        log = staticmethod(logs.append)
    monkeypatch.setattr(KW, "scheduler_current", lambda ap: True)
    monkeypatch.setattr(KW, "hub_launch_held", lambda *a: False)
    monkeypatch.setattr(KW, "tool_skew_refuse", lambda *a: False)
    cfg = {"dies": {"kv": die(die_gen_env={"OT_SIGNED_VIEW_SHA": "/srv/s/kit-ops-6/f.json"})}}
    st = {}
    r = {"item": "kv3_x"}
    assert KW.launch(AP, cfg, st, "kv", r, "hub") is None
    assert KW.launch(AP, cfg, st, "kv", r, "hub") is None
    assert len([m for m in logs if "outside the die src tree" in m]) == 1             # logged once per change


def test_adopt_rows_alert_for_an_off_die_with_no_current_event_rows():
    logs, posts = [], []

    class AP:
        DRY = False
        log = staticmethod(logs.append)
        coord_append = staticmethod(lambda f, t: posts.append(t))
    cfg = {"dies": {"qwen_kvsys": {"enabled": True, "src": "/t/new", "event": "KV-HG6", "owner_lane": "KV-HG-OPUS", "gate": {}}}}
    st = {"adopt_seen": {"qwen_kvsys": {"src": "/t/old", "sig": ["KV-HG5", None]}},
          "items": {"a": {"die": "qwen_kvsys", "item": "x", "event": "KV-HG5", "status": "CANCELLED"}}}
    KW.adopt_rows_tick(AP, cfg, st)                    # the switch is seen
    KW.adopt_rows_tick(AP, cfg, st)                    # tick 1
    assert not posts
    KW.adopt_rows_tick(AP, cfg, st)                    # tick 2: no current-event row, plan not probed
    KW.adopt_rows_tick(AP, cfg, st)
    assert len(posts) == 1 and "KV-HG6" in posts[0] and "gate_events_extra" in posts[0] and "OFF" in posts[0]
    st["items"]["b"] = {"die": "qwen_kvsys", "item": "x", "event": "KV-HG6", "status": "ENQUEUED"}
    st["adopt_seen"]["qwen_kvsys"] = {"src": "/t/old2", "sig": ["KV-HG5", None]}
    KW.adopt_rows_tick(AP, cfg, st)
    for _ in range(3):
        KW.adopt_rows_tick(AP, cfg, st)
    assert len(posts) == 1                              # a die with a current-event row is quiet
