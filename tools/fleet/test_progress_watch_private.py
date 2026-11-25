"""PRIVATE-LAUNCH-1124: private-spec launches (autopilot/private_specs dirs, ot-run submits of private kits) count as launches of their
die, so a die launching only private kits is not alerted NO-PROGRESS; an alert names the last private launch too.  Alert-only as before."""
import json
import os
import pathlib
import sys
import tempfile
from datetime import datetime as D, timedelta

H = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import progress_watch as P

NOW = D(2026, 11, 24, 21, 0)
STATE = {"eligible": {"s81": 12}, "known": ["s81"]}


def wave(t="2026-11-24 10:42:00"):
    return P.parse_lines([f"{t} PST AUTOPILOT: KIT-WAVE LAUNCH s81/a (type, 1 replicas)"])


def alerts(ev):
    return [f for f in P.detect(ev, NOW, STATE) if f["cls"] == "NO-PROGRESS" and f["die"] == "s81"]


def test_wave_silent_die_alerts_without_private_launches():
    got = alerts(wave())
    assert got and "0 KIT-WAVE LAUNCH for 618 min" in got[0]["text"] and "private-spec launches" in got[0]["text"]


def test_recent_private_launch_keeps_the_die_quiet():
    ev = wave() + [{"t": NOW - timedelta(minutes=12), "kind": "private_launch", "die": "s81", "src": "ot-run S81-ALLFIX-INT x"}]
    assert alerts(ev) == []


def test_old_private_launch_is_named_in_the_alert():
    ev = wave() + [{"t": NOW - timedelta(minutes=90), "kind": "private_launch", "die": "s81", "src": "private_specs/L/s81_x_1124193000"}]
    got = alerts(ev)
    assert got and "last 19:30 private_specs/L/s81_x_1124193000" in got[0]["text"]


def test_private_launch_of_another_die_does_not_count():
    ev = wave() + [{"t": NOW - timedelta(minutes=5), "kind": "private_launch", "die": "s81_head", "src": "x"}]
    assert alerts(ev)


def test_private_spec_dirs_give_die_and_time():
    root = pathlib.Path(tempfile.mkdtemp())
    for lane, n in (("S81-ALLFIX-INT", "s81_ot_s81sl_leaf__t53__cl958451dd_1124203147"), ("HEAD-W", "s81_head_hd_x_1124205000"),
                    ("QC", "qwen_compute_slw_su_c__cl19bb38ef_1124210740"), ("OLD", "s81_y_1120100000"), ("JUNK", "notes_txt")):
        (root / lane / n).mkdir(parents=True)
    ev = sorted(P.private_spec_events(str(root), NOW, NOW - timedelta(hours=25)), key=lambda e: e["t"])
    assert [(e["die"], e["t"]) for e in ev] == [("s81", D(2026, 11, 24, 20, 31, 47)), ("s81_head", D(2026, 11, 24, 20, 50, 0))]


def test_ledger_private_kit_submits_count_per_die():
    f = pathlib.Path(tempfile.mkdtemp()) / "submit.jsonl"
    t = D(2026, 11, 24, 20, 49, 20)
    import zoneinfo
    ts = t.replace(tzinfo=zoneinfo.ZoneInfo("America/Los_Angeles")).timestamp()
    recs = [{"ts": ts, "dir": "/srv/x/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/ot_s81sl_leaf__t53_1124203147", "lane": "S81-ALLFIX-INT"},
            {"ts": ts, "dir": "/srv/x/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/item_a", "lane": "W"},          # wave kit: the log counts it
            {"ts": ts, "dir": "/srv/opentallas-scratch2/claude/FLOW-OPS-R3-zl", "lane": "FLOW-OPS-R3"}]
    f.write_text("".join(json.dumps(r) + "\n" for r in recs) + "not json\n")
    ev = P.ledger_private_events(str(f), NOW, NOW - timedelta(hours=25))
    assert [(e["die"], e["t"]) for e in ev] == [("s81", t)] and "S81-ALLFIX-INT" in ev[0]["src"]
