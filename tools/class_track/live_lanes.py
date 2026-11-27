#!/usr/bin/env python3
"""live_lanes.py -- the live-lane map (P-DEAD-LANE-ROUTING, FABLE-FLOW-0847 A16, COORD 11-26).

lanes/LIVE-LANES.tsv: lane, die, classes, agent, last_post, status (live|dead), integrator.
Every watchdog notice (PLATEAU, NOPROG, SMELL, FLEET-WATCH, VIS-REOWN, CBC-RULES, OWNERS-SWEEP) is posted through post.sh, whose
tools/post_redirect.py consults this map: a notice addressed to a `dead` lane also reaches its die integrator (the `integrator` column).

    live_lanes.py build --spec live_spec.tsv --dead-from COORD-LANES-1125-2005.tsv --posts lanes/posts --out lanes/LIVE-LANES.tsv
    live_lanes.py resolve NAME [--map lanes/LIVE-LANES.tsv]         -> the lane that should receive a notice for NAME
spec columns: lane, die, classes, agent
"""
import argparse
import csv
import os
import re
import sys

COLS = ["lane", "die", "classes", "agent", "last_post", "status", "integrator"]
INTEGRATOR = {"S81": "S81-INT-R2", "HEAD": "HEAD-INT-R2", "QC": "QC-INT-R2", "KV": "KV-INT-R2", "FLEET": "FLEET-OPS-R4"}
STAMP = re.compile(r"^- (\d{4}-\d{2}-\d{2} \d{2}:\d{2})")
DIE_TOKEN = re.compile(r"(?:^|[-_.])(S81|HEAD|QC|KV|FLEET)(?:[-_.]|$)", re.I)


def read_tsv(path):
    try:
        with open(path, newline="") as fh:
            return list(csv.DictReader(fh, delimiter="\t"))
    except OSError:
        return []


def post_file(posts_dir, lane):
    """posts/<lane>.md, case-insensitively (post.sh folds a lane to its first spelling: head-int-r2.md for HEAD-INT-R2)."""
    p = os.path.join(posts_dir, lane + ".md")
    if os.path.exists(p):
        return p
    cf = (lane + ".md").casefold()
    try:
        for f in os.listdir(posts_dir):
            if f.casefold() == cf:
                return os.path.join(posts_dir, f)
    except OSError:
        pass
    return p


def last_post(posts_dir, lane):
    last = ""
    try:
        with open(post_file(posts_dir, lane), errors="replace") as fh:
            for ln in fh:
                m = STAMP.match(ln)
                if m:
                    last = m.group(1)
    except OSError:
        pass
    return last


def infer_die(lane):
    m = DIE_TOKEN.search(lane)
    return m.group(1).upper() if m else ""


def build(spec, dead_rows, posts_dir, active_since=""):
    out, seen = [], set()
    for r in spec:
        d = r["die"].upper()
        lp = last_post(posts_dir, r["lane"])
        # COORD 11-26 14:52: a lane with no post in the window is pruned from the live map (die integrators stay: notices fall through to them)
        live = (not active_since) or r["lane"] in INTEGRATOR.values() or (lp != "" and lp >= active_since)
        out.append({"lane": r["lane"], "die": d, "classes": r.get("classes", ""), "agent": r.get("agent", "") or "-",
                    "last_post": lp, "status": "live" if live else "dead", "integrator": INTEGRATOR.get(d, "COORD")})
        seen.add(r["lane"])
    for r in dead_rows:
        if r["lane"] in seen:
            continue
        d = (r.get("die") or infer_die(r["lane"])).upper()
        out.append({"lane": r["lane"], "die": d, "classes": r.get("owns", ""), "agent": r.get("claude_agent", "") or "-",
                    "last_post": last_post(posts_dir, r["lane"]), "status": "dead", "integrator": INTEGRATOR.get(d, "COORD")})
        seen.add(r["lane"])
    if active_since:  # every other lane with a posts file: live when it posted since `active_since` ("YYYY-MM-DD HH:MM"), else dead
        have = {x["lane"].casefold() for x in out}
        for f in sorted(os.listdir(posts_dir)):
            if not f.endswith(".md") or f[:-3].casefold() in have:
                continue
            lane = f[:-3]
            lp = last_post(posts_dir, lane)
            d = infer_die(lane)
            out.append({"lane": lane, "die": d, "classes": "", "agent": "-", "last_post": lp,
                        "status": "live" if lp and lp >= active_since else "dead", "integrator": INTEGRATOR.get(d, "COORD")})
            have.add(lane.casefold())
    return out


def resolve(name, rows):
    """lane that should receive a notice for NAME: itself when live or unknown, else the die integrator of a dead lane."""
    for r in rows:
        if r["lane"].casefold() == name.casefold():
            return r["lane"] if r["status"] == "live" else r["integrator"]
    return name


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--spec", required=True)
    b.add_argument("--dead-from", default="")
    b.add_argument("--posts", required=True)
    b.add_argument("--out", required=True)
    b.add_argument("--dead-out", default="", help="write the dead rows here (post_redirect reads both files); --out then holds live lanes only")
    b.add_argument("--active-hours", type=float, default=0, help="also add every posting lane: live when it posted within this many hours")
    r = sub.add_parser("resolve")
    r.add_argument("name")
    r.add_argument("--map", default="/home/ubuntu/coord/lanes/LIVE-LANES.tsv")
    a = ap.parse_args(argv)
    if a.cmd == "resolve":
        print(resolve(a.name, read_tsv(a.map)))
        return 0
    since = ""
    if a.active_hours:
        import datetime
        since = (datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-8))) - datetime.timedelta(hours=a.active_hours)).strftime("%Y-%m-%d %H:%M")
    rows = build(read_tsv(a.spec), read_tsv(a.dead_from) if a.dead_from else [], a.posts, since)
    live_rows = [x for x in rows if x["status"] == "live"] if a.dead_out else rows
    for path, rs in ((a.out, live_rows), (a.dead_out, [x for x in rows if x["status"] != "live"])):
        if not path:
            continue
        with open(path, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLS, delimiter="\t", lineterminator="\n")
            w.writeheader()
            w.writerows(rs)
    print(f"{sum(1 for x in rows if x['status'] == 'live')} live, {sum(1 for x in rows if x['status'] == 'dead')} dead -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
