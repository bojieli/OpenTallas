"""FLOW-OPS-0900 (FABLE-FLOW-0745 d): failure classes stay with the successor chain instead of bouncing at stand-downs."""
import importlib.util
import json
import os
import subprocess
import time
from pathlib import Path

H = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("fr_ho", H / "fail_route.py")
fr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fr)

NOW = 1795300000.0


def _coord(tmp, status_rows, posts=""):
    c = tmp / "coord"
    (c / "lanes/posts").mkdir(parents=True)
    (c / "autopilot").mkdir()
    (c / "lanes/COORD-REVIEW-QUEUE.md").write_text(posts)
    (c / "lanes/LANE-STATUS.tsv").write_text("lane\tstatus\tsuccessor\tupdated\tnote\n" + "".join("\t".join(r) + "\n" for r in status_rows))
    (c / "autopilot/kit_wave_state.json").write_text("{}")
    return c


def _cls(owner, cid="abc1234567"):
    return {"kit|x": dict(die="s81", kind="kit", label="s81/place/X err", items={"leaf_t11": NOW}, fams={"leaf_t11"}, owner=owner, cid=cid, forced="")}


def _run(c, st, classes, posts=None):
    sent_texts = []
    sf = c / "state.json"
    sf.write_text(json.dumps(st))
    orig = fr.build_classes
    fr.build_classes = lambda *a, **k: classes
    try:
        sent, fail, _ = fr.run(c, sf, "/dev/null", now=NOW, poster=lambda _p, t: (sent_texts.append(t), True)[1])
    finally:
        fr.build_classes = orig
    return sent, sent_texts, json.loads(sf.read_text())


def test_stood_down_owner_hands_over_to_live_successor_once(tmp_path):
    c = _coord(tmp_path, [("S81-A", "stood-down", "S81-B", "x", ""), ("S81-B", "stood-down", "S81-C", "x", "")])
    st = {"classes": {"S81-A|abc1234567": {"t": NOW - 3600, "items": ["leaf_t11"], "label": "s81/place/X err", "lane_posted": int(NOW - 600)}}}
    # the router picked some other die lane this round; the class must go to the live end of S81-A's chain instead
    sent, texts, st2 = _run(c, st, _cls("S81-OTHER"))
    assert [s[0] for s in sent] == ["HANDOVER"] and "S81-C" in texts[0] and "open 60 min" in texts[0] and "no second one" in texts[0]
    assert list(st2["classes"]) == ["S81-C|abc1234567"]
    rec = st2["classes"]["S81-C|abc1234567"]
    assert rec["t"] == NOW - 3600 and rec["owners"] == ["S81-A", "S81-C"] and rec["lane_posted"]
    sent, texts, st3 = _run(c, st2, _cls("S81-C"))        # next run: no new NEEDS-ACTION, no second NEEDS-LANE
    assert sent == []


def test_ack_from_chain_counts_and_window_restarts_for_new_owner(tmp_path):
    c = _coord(tmp_path, [("S81-A", "stood-down", "S81-C", "x", "")])
    st = {"classes": {"S81-C|abc1234567": {"t": NOW - 7200, "t_owner": NOW - 60, "owners": ["S81-A", "S81-C"], "items": ["leaf_t11"]}}}
    sent, _, _ = _run(c, st, _cls("S81-C"))
    assert sent == []                                         # 1 min with the new owner: no NEEDS-LANE yet although first seen 2 h ago
    posts = "- 2026-11-21 08:30 PST RESULT [S81-A -> COORD] abc1234567 cause found\n"
    c2 = _coord(tmp_path / "b", [("S81-A", "stood-down", "S81-C", "x", "")], posts)
    st = {"classes": {"S81-C|abc1234567": {"t": NOW - 7200, "t_owner": NOW - 3600, "owners": ["S81-A", "S81-C"], "items": ["leaf_t11"]}}}
    fr_now = fr.stamp_epoch("2026-11-21 08:30")
    st["classes"]["S81-C|abc1234567"]["t"] = fr_now - 60
    st["classes"]["S81-C|abc1234567"]["t_owner"] = fr_now - 60
    sf = c2 / "state.json"; sf.write_text(json.dumps(st))
    orig = fr.build_classes
    fr.build_classes = lambda *a, **k: _cls("S81-C")
    try:
        sent, _, _ = fr.run(c2, sf, "/dev/null", now=fr_now + 120, poster=lambda *_: True)
    finally:
        fr.build_classes = orig
    assert sent == [] and json.loads(sf.read_text())["classes"]["S81-C|abc1234567"].get("acked")


def test_stood_down_lane_is_never_live():
    posts = [{"lane": "S81-A", "t": NOW - 60}, {"lane": "S81-C", "t": NOW - 600}]
    st = {"S81-A": ("stood-down", "S81-C", "")}
    assert set(fr.live_lanes(posts, NOW, 3, st)) == {"S81-C"}
    assert set(fr.live_lanes(posts, NOW, 3)) == {"S81-A", "S81-C"}         # no status file: old behaviour


def test_open_relays_text_for_stand_down(tmp_path):
    sf = tmp_path / "s.json"
    sf.write_text(json.dumps({"classes": {"L1|aaaa000001": {"t": NOW - 600, "items": ["a", "b"], "label": "kv/grt/X"},
                                          "L1|aaaa000002": {"t": NOW, "items": ["c"], "acked": 1},
                                          "L2|aaaa000003": {"t": NOW, "items": ["d"]}}}))
    t = fr.open_relays_text(sf, "L1", now=NOW)
    assert t.count("FAIL-CLASS") == 1 and "aaaa000001" in t and "open 10 min" in t and "a, b" in t
    r = subprocess.run(["python3", "-I", str(H / "fail_route.py"), "--open-relays", "L1", "--state", str(sf)], capture_output=True, text=True)
    assert r.returncode == 0 and "aaaa000001" in r.stdout


def test_stand_down_script_writes_open_relays_block():
    sh = (H.parent / "bin/stand-down.sh").read_text()
    assert '--open-relays "$lane"' in sh and "## OPEN-RELAYS from" in sh and 'lanes/LANE-STATUS.tsv $extra' in sh
