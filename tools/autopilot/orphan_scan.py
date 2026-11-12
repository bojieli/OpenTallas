#!/usr/bin/env python3
"""orphan_scan.py -- READ-ONLY census of running docker containers against the hub's wave/job rows (FAILFAST-1 scope 2, COORD 11-12).

    python3 -I tools/autopilot/orphan_scan.py [--hosts a,b] [--json OUT] [--lane-hours 3]

A container is an ORPHAN CANDIDATE when its kit (the /work mount, or for an ot-job isolated copy the original kit named in
.ot-job/job.json) maps only to CANCELLED / DONE-* / FAIL / SUPERSEDED rows, or to no row at all.  Candidates whose item or kit dir
is named by a lane posting in COORD-REVIEW-QUEUE.md within --lane-hours are LANE-OWNED and listed separately.  Sends no signal.
"""
import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
import zlib
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
HOSTS = "epyc2,epyc4,epyc7,epyc8,epyc9,intel1"
LIVE_JOB = ("RUNNING", "LAUNCHING", "ENQUEUED", "WAIT-DEP", "WAIT-GEOM", "WAIT-PARENT")
GENERIC = {"work", "gen", "run", "items", "kit-wave", "runs", "kits", "claude", "srv", "ot-jobs", "attempt", "base", "tmp"}
SELF_TAGS = ("AUTOPILOT", "KIT-WAVE", "DISK-", "FAILFAST-1", "VERDICT-TRIAGE", "WATCHDOG", "COORD")

HUB_INDEX = r'''
import json, os, re, sys, time
H = os.path.expanduser("~/coord")
rows = []
for k, v in json.load(open(H + "/autopilot/state.json"))["jobs"].items():
    kit = str(v.get("kit") or "")
    rows.append(["job", kit.split(":", 1)[-1].rstrip("/"), v.get("status"), v.get("kind") or v.get("cls") or "", v.get("id"), v.get("updated"), v.get("lane") or ""])
wave = []
for k, r in json.load(open(H + "/autopilot/kit_wave_state.json")).get("items", {}).items():
    kit = str(r.get("kit") or "")
    wave.append([r.get("die"), r.get("event"), r.get("item"), r.get("attempt"), r.get("status"), r.get("q_status"), str(r.get("class") or r.get("q_class") or ""), r.get("updated")])
    rows.append(["wave", kit.split(":", 1)[-1].rstrip("/"), r.get("status") + ("/" + str(r.get("q_status")) if r.get("q_status") else ""),
                 str(r.get("class") or r.get("q_class") or ""), "%s|%s|a%s" % (r.get("die"), r.get("item"), r.get("attempt")), r.get("updated"), ""])
now = time.time()
q = []
for ln in open(H + "/lanes/COORD-REVIEW-QUEUE.md", errors="replace").read().splitlines()[-4000:]:
    m = re.match(r"- (\d{4}-\d\d-\d\d) (\d\d:\d\d) \w+ (.*)", ln)
    if m:
        t = time.mktime(time.strptime(m[1] + " " + m[2], "%Y-%m-%d %H:%M"))
        if now - t < 6 * 3600:
            q.append([t, m[3][:700]])
print(json.dumps({"rows": [r for r in rows if r[1]], "wave": wave, "queue": q, "now": now}))
'''


def b64py(src):
    return "python3 -I -c \"import base64,zlib;exec(zlib.decompress(base64.b64decode('%s')).decode(),{'__name__':'__main__'})\"" % \
        base64.b64encode(zlib.compress(src.encode())).decode()


def ssh(host, cmd, timeout=150):
    p = subprocess.run(["timeout", str(timeout + 10), "ssh", "-n", "-o", "ControlPath=none", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", host, cmd],
                       capture_output=True, text=True, timeout=timeout + 20)
    return json.loads(p.stdout.strip().splitlines()[-1])


def norm(p):
    """scratch2/scratch3 are symlinked aliases: key a kit by the part after /claude/"""
    p = (p or "").rstrip("/")
    return p.split("/claude/", 1)[-1] if "/claude/" in p else p


def tokens(origin):
    """names that identify the build: the wave item (never the event / die dirs) or the last two dirs of a lane kit"""
    p = (origin or "").rstrip("/")
    m = re.search(r"/items/([^/]+)", p)
    parts = [m[1], p.split("/")[-1]] if m else p.split("/")[-2:]
    out = []
    for t in parts:
        t = re.sub(r"-(route|place|synth|cts)-.*$", "", t)
        if len(t) >= 6 and t not in GENERIC and not re.fullmatch(r"[0-9a-f]{8,}", t) and not t.startswith("kw") and t not in out:
            out.append(t)
    return out


def lane_dir(origin):
    """the lane's own top dir under /claude/ (hbm-cores-b, die-s81-85, cplqc ...); '' for a wave root (kw*, *-wave-*)"""
    p = (origin or "").rstrip("/")
    if "/claude/" not in p:
        return ""
    d = p.split("/claude/", 1)[1].split("/")[0]
    return "" if re.match(r"(kw\d|codex-.*wave|.*-wave-|qc-wave|ot-jobs|autopilot)", d) else d


def lane_key(text):
    return re.sub(r"\d+$", "", re.sub(r"[^a-z0-9]", "", text.lower()))


def census_lines(containers, queue, limit=6):
    """queue lines naming more than `limit` different containers' kits are census / bulk posts (one lane listing the fleet), not
    ownership claims: -> set of their indexes"""
    toks = {t for c in containers for t in tokens(c.get("origin") or c.get("work"))}
    return {i for i, (_t, text) in enumerate(queue) if sum(1 for t in toks if t in text) > limit}


WAVE_RX = re.compile(r"/kit-wave/([^/\s]+)/([^/\s]+)/items/([^/\s]+)(?:/attempt_(\d+))?(?=[/\s]|$)")


def wave_rows(org, wave):
    """kit-wave rows of this container's (die, event, item): -> (attempt N of the container, [row]) or (None, [])"""
    m = WAVE_RX.search(org or "")
    if not m:
        return None, []
    return int(m[4] or 1), [w for w in wave if w[0] == m[1] and w[1] == m[2] and w[2] == m[3]]


def live_wave(w):
    st, q = w[4], w[5]
    return st in ("RUNNING", "ROUTE-HELD", "RETRY-INFRA") or (st == "ENQUEUED" and q not in ("FAIL", "SIGNED", "CANCELLED"))


def classify(c, by_path, queue, now, lane_hours=3.0, skip=(), wave=()):
    """-> (verdict, row_status, owner) for one container dict.  verdict LIVE | ORPHAN | LANE"""
    org = (c.get("origin") or c.get("work") or "").rstrip("/")
    rows = by_path.get(norm(org), [])
    n, wrows = wave_rows(org, wave)
    live = [r for r in rows if r[2] and r[2].split("/")[0] in LIVE_JOB and not (r[2].startswith("ENQUEUED/") and r[2].split("/")[1] in ("FAIL", "SIGNED", "CANCELLED"))]
    if live:
        return "LIVE", live[0][2], ""
    if n is not None and wrows:
        same = [w for w in wrows if w[3] == n]
        if any(live_wave(w) for w in same):
            return "LIVE", "wave %s a%s" % (same[0][4], n), ""
        newer = [w for w in wrows if (w[3] or 0) > n]
        top = max(wrows, key=lambda w: w[3] or 0)
        status = "wave a%s %s (row now a%s %s%s)" % (n, same[0][4] + ("/" + str(same[0][5]) if same[0][5] else "") if same else "no a%s row" % n,
                                                    top[3], top[4], ("/" + str(top[5])) if top[5] else "")
        rows = []
    elif rows:
        last = max(rows, key=lambda r: r[5] or 0)
        status = "%s %s%s" % (last[0], last[2], (" " + last[3]) if last[3] else "")
    if not rows and not wrows:
        status = "no row"
    dead = status != "no row"                       # a row exists and no live row wants this container: a leak whoever posted
    toks = tokens(org) + tokens(c.get("work"))
    owners = {}
    for i, (t, text) in enumerate(queue):
        if now - t > lane_hours * 3600 or i in skip:
            continue
        if any(tok in text for tok in toks):
            m = re.search(r"\[([A-Z][A-Z0-9_.+-]{2,})[ ,\]]", text[:200])
            tag = m[1] if m else ""
            if tag and not tag.startswith(SELF_TAGS):
                owners[tag] = max(owners.get(tag, 0), t)
    ld = lane_key(lane_dir(org)) if lane_dir(org) else ""
    if ld and len(ld) >= 4:
        for i, (t, text) in enumerate(queue):
            if now - t > lane_hours * 3600 or i in skip:
                continue
            m = re.search(r"\[([A-Z][A-Z0-9_.+-]{2,})[ ,\]]", text[:200])
            tag = m[1] if m else ""
            k = lane_key(tag)
            if tag and not tag.startswith(SELF_TAGS) and k and (k.startswith(ld) or ld.startswith(k)):
                owners[tag] = max(owners.get(tag, 0), t)
    if owners:
        tag, t = max(owners.items(), key=lambda kv: kv[1])
        return ("ORPHAN" if dead else "LANE"), status, "%s posted %.1f h ago" % (tag, (now - t) / 3600.0)
    return "ORPHAN", status, ""


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--hosts", default=HOSTS)
    a.add_argument("--json")
    a.add_argument("--lane-hours", type=float, default=3.0)
    x = a.parse_args(argv)
    hub = ssh("intel2", b64py(HUB_INDEX), 120)
    by_path = {}
    for r in hub["rows"]:
        by_path.setdefault(norm(r[1]), []).append(r)
    src = open(os.path.join(HERE, "orphan_hostscan.py")).read()
    hosts = [h for h in x.hosts.split(",") if h]
    with ThreadPoolExecutor(len(hosts)) as ex:
        res = list(ex.map(lambda h: _safe(h, src), hosts))
    table = {"LIVE": [], "ORPHAN": [], "LANE": []}
    skip = census_lines([c for r in res for c in r.get("containers", [])], hub["queue"])
    for h, r in zip(hosts, res):
        for c in r.get("containers", []):
            v, status, owner = classify(c, by_path, hub["queue"], hub["now"], x.lane_hours, skip, hub["wave"])
            table[v].append(dict(c, host=h, row=status, owner=owner))
    if x.json:
        json.dump({"table": table, "scopes": {h: r.get("scopes") for h, r in zip(hosts, res)}}, open(x.json, "w"), indent=1)
    out = []
    for title, key in (("ORPHAN CANDIDATES (dead row or no row, no lane post in %g h)" % x.lane_hours, "ORPHAN"), ("LANE-OWNED (dead or no row, lane posted in %g h)" % x.lane_hours, "LANE")):
        out += ["", title, "| host | container | row status | age h | threads | GB | owner | kit |", "|---|---|---|---|---|---|---|---|"]
        for c in sorted(table[key], key=lambda c: (c["host"], -(c["age_h"] or 0))):
            out.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (c["host"], c["name"], c["row"], c["age_h"], c["threads"], c["rss_gb"], c["owner"], (c.get("origin") or c.get("cmd") or "")[-90:]))
    n = lambda k: (len(table[k]), round(sum(c["rss_gb"] for c in table[k]), 1), sum(c["threads"] for c in table[k]))
    out += ["", "live-row containers %d (%.1f GB, %d threads); orphan candidates %d (%.1f GB, %d threads); lane-owned %d (%.1f GB, %d threads)" % (n("LIVE") + n("ORPHAN") + n("LANE"))]
    print("\n".join(out))


def _safe(h, src):
    try:
        return ssh(h, b64py(src))
    except Exception as e:                       # noqa: one dead host must not hide the others
        return {"containers": [], "error": repr(e)[:160]}


if __name__ == "__main__":
    sys.exit(main())
