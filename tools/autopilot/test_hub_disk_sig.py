"""FLOW-HEALTH-1 11-15 (FABLE-FLOW-1200 items 2 and 6): hub disk precondition; fail signature keyed on (item, stage, class)"""
import types
import kit_wave as KW


class AP:
    def __init__(self):
        self.logs, self.q = [], []

    def log(self, m):
        self.logs.append(m)

    def coord_append(self, rel, line):
        self.q.append(line)


def vfs(free_gb):
    return lambda p: types.SimpleNamespace(f_bavail=int(free_gb[p] * 2**30), f_frsize=1)


def test_low_scratch2_refuses_with_both_paths_named():
    why = KW.hub_disk_low({}, statvfs=vfs({"/srv/opentallas-scratch2": 28, "/": 300}))
    assert why.startswith("hub disk low") and "scratch2 28 GB" in why and "/ " not in why.split(";")[0] + "x"
    assert KW.hub_disk_low({}, statvfs=vfs({"/srv/opentallas-scratch2": 100, "/": 300})) == ""
    assert KW.hub_disk_low({"hub_free_min_gb": 0}, statvfs=vfs({"/srv/opentallas-scratch2": 1, "/": 1})) == ""


def test_missing_path_is_not_a_reason():
    def sv(p):
        raise OSError()
    assert KW.hub_disk_low({}, statvfs=sv) == ""


def test_gate_posts_once_and_stops_launches(monkeypatch):
    ap, st, cfg = AP(), {}, {"enabled": True, "dies": {"d": {"enabled": True}}}
    monkeypatch.setattr(KW, "hub_disk_low", lambda cfg, **k: "hub disk low: / 10 GB free < 64 GB")
    KW.hub_disk_gate(ap, cfg, st)
    KW.hub_disk_gate(ap, cfg, st)
    assert len(ap.q) == 1 and "STATE" in ap.q[0]
    assert KW.stop_reason(cfg, "d", "/nonexistent") == "hub disk low: / 10 GB free < 64 GB"
    monkeypatch.setattr(KW, "hub_disk_low", lambda cfg, **k: "")
    KW.hub_disk_gate(ap, cfg, st)
    assert len(ap.q) == 2 and "resume" in ap.q[1] and KW.stop_reason(cfg, "d", "/nonexistent") is None


def test_alternating_text_same_stage_is_one_signature():
    a = KW.fail_signature("FLOW", "KW_ROAM probe host epyc7 @kit_rtl: roam failed", "kit_rtl")
    b = KW.fail_signature("FLOW", "bind.py: error: missing /srv/x/y.sv @kit_rtl: bind", "kit_rtl")
    assert a == b == ("FLOW", "FLOW|kit_rtl")
    assert KW.fail_signature("FLOW", "x @gen: y", "gen") != a
    assert KW.fail_signature("INFRA", "x @gen: y", "gen") is None


def test_three_alternating_fails_reach_the_cap():
    st = {}
    rec = {"die": "d", "item": "i", "stage": "kit_rtl", "event": "e"}
    for i, w in enumerate(["KW_ROAM a @kit_rtl: p", "bind.py: error b @kit_rtl: q", "KW_ROAM c @kit_rtl: r"]):
        c = KW.note_fail_sig(st, dict(rec, attempt=i), "FLOW", w)
    assert c["n"] == 3
