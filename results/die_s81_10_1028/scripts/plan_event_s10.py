#!/usr/bin/env python3
"""DIE-S81-10 S81 plan event (pre-F1 part; die-local plan input, no shared-tool edit).
plan_s5 (d29050658673) + CORELAT-SQ-1 early core taps (s81_tap_delta.json, incl. DIE-S81-8 ve/vn means) +
clock.tap_window {window_ps W} + clock.seam_hold {sender_ps, seam_ps}.
F1 relays (FLOW joint4) and the CA +1 cycles are NOT plan geometry here: F1 is still running; the CA cycles are
planner output (CA-OCV-1 count_align_plan/bind --sta-clock-ocv), not a plan field.
Taps whose delta xy is TO-DO (ve_m / vn_a / vn_b: plan LEF absent, pins_file present) get the transformed pins_file
clock pin; the delta's pin name 'ck' is replaced by the pins_file clock pin name.
usage: plan_event_s10.py PLAN_IN DELTA ROOT PLAN_OUT [--window 180] [--sender 0] [--seam 40]"""
import argparse, collections, hashlib, json
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("plan"); ap.add_argument("delta"); ap.add_argument("root"); ap.add_argument("out")
ap.add_argument("--window", type=float, default=180.0); ap.add_argument("--sender", type=float, default=0.0)
ap.add_argument("--seam", type=float, default=40.0)
a = ap.parse_args()
raw = Path(a.plan).read_bytes(); P = json.loads(raw); D = json.load(open(a.delta))
assert hashlib.sha256(raw).hexdigest()[:12] == D["plan_sha"], "delta was made on another plan"
stat = collections.Counter(); log = []


def pins_file_clock(c):
    pf = Path(a.root) / "physical/die_plan/s81" / c["pins_file"]
    pins = json.load(open(pf))["pins"]
    ck = [p for p in pins if p["name"] in ("clk", "ck", "clock")]
    assert len(ck) == 1, (c["inst"], [p["name"] for p in ck])
    p = ck[0]; x, y = c["origin_um"]; w, h = c["outline_um"]; px, py = p["x"], p["y"]; o = c.get("orient", "R0")
    if o in ("MY", "R180"): px = w - px
    if o in ("MX", "R180"): py = h - py
    dx, dy = c.get("track_offset_um", [0.0, 0.0])
    return p["name"], [round(x + dx + px, 3), round(y + dy + py, 3)]


for tn, td in D["types"].items():
    t = P["partition_types"][tn]
    ck = t.setdefault("clock", {})
    taps = ck.setdefault("taps", [])
    hc = {c["inst"]: c for c in t.get("hard_cores", [])}
    for r in td["rows"]:
        old = [i for i, tp in enumerate(taps) if tp.get("kind") == "core" and
               (tp["name"] == r["name"] or tp["name"] == r["inst"] or tp["name"].startswith(r["inst"] + "."))]
        if r.get("new"):
            n = dict(r["new"])
            if isinstance(n["xy"], str):
                pin, xy = pins_file_clock(hc[r["inst"]])
                n["name"], n["xy"] = f"{r['inst']}.{pin}", xy
                n["note"] += f"; xy = pins_file clock pin {pin} transformed (DIE-S81-10)"
                stat["xy_from_pins_file"] += td["count"]
            n.pop("early_tt_ps", None); n.pop("early_ff_ps", None)
            for i in reversed(old):
                taps.pop(i)
            taps.append(n); ck["core_taps"] = "early"
            stat["early_retap" if old else "early_new"] += td["count"]
        elif r["action"].startswith("DROP"):
            for i in reversed(old):
                taps.pop(i)
            stat["drop"] += td["count"]
    if not any(tp.get("kind") == "core" for tp in taps) and ck.get("core_taps") == "early":
        ck.pop("core_taps"); stat["type_core_taps_cleared"] += 1
P["clock"]["seam_hold"] = dict(sender_ps=a.sender, seam_ps=a.seam,
                               note="DIE-S81-10: legacy-equivalent seam contract (receiver -40 / sender 0); S81 has 0 seam pairs (all crossings count-aligned)")
P["clock"]["tap_window"] = dict(window_ps=a.window,
                                note="DIE-S81-10 (COORD 06:47): one window for every type; needed 159.84 incl OCV (bk_sel), <= T/4")
early_types = sum(1 for t in P["partition_types"].values() if (t.get("clock") or {}).get("core_taps") == "early")
cnt = collections.Counter(x["type"] for x in P["partitions"])
early_parts = sum(cnt[tn] for tn, t in P["partition_types"].items() if (t.get("clock") or {}).get("core_taps") == "early")
out = json.dumps(P, indent=1) + "\n"
Path(a.out).write_text(out)
print("PLAN_EVENT", a.out, hashlib.sha256(out.encode()).hexdigest()[:12], dict(stat),
      "early types", early_types, "early partitions", early_parts, "of", len(P["partitions"]))
