#!/usr/bin/env python3
"""CLEAN-ALL-1115 (COORD ruling 11-16): narrow the handoff/queue-text guard.
A path is protected by TEXT only if the reference is in (a) a file under lanes/handoff or autopilot/ modified in the last H hours (72),
or (b) a COORD-REVIEW-QUEUE line (with its indented continuation lines) whose timestamp is within the last H hours.  Queued jobs, waiter
cmdlines and units stay protected by the process/state scan (not here).  Plus the tree_switch markers: the newest marker per die (aliases
head->s81_head, qc->qwen_compute, kv->qwen_kvsys) and every tree carrying the newest tools_sha are kept; an older marker of a die that has a
newer one no longer protects its tree (v1 trees stay protected until that die's v2 marker exists).
usage: ot_cleanup_textrefs.py COORD_DIR HANDOFF_MARKER_DIR OUT_REFS OUT_KEEPN [hours]"""
import glob, json, os, re, sys, time
from datetime import datetime
PAT = re.compile(r"/srv/opentallas-scratch[23]*/claude/[A-Za-z0-9._/-]+")
ISO = re.compile(r"^- (\d{4})-(\d\d)-(\d\d) (\d\d):(\d\d)")
MD = re.compile(r"^- (\d\d)-(\d\d) (\d\d):(\d\d)")
ALIAS = {"head": "s81_head", "qc": "qwen_compute", "kv": "qwen_kvsys"}


def canon(p):
    return p.replace("opentallas-scratch3", "opentallas-scratch2").rstrip("/.,")


def line_time(line, year):
    m = ISO.match(line)
    if m:
        return datetime(*map(int, m.groups())).timestamp()
    m = MD.match(line)
    if m:
        mo, d, h, mi = map(int, m.groups())
        return datetime(year, mo, d, h, mi).timestamp()
    return None


def text_refs(coord, now=None, hours=72):
    now = now or time.time(); cut = now - hours * 3600; refs = set()
    year = datetime.fromtimestamp(now).year
    files = [f for pat in ("lanes/handoff/*", "autopilot/*") for f in glob.glob(os.path.join(coord, pat)) if os.path.isfile(f)]
    for f in files:
        try:
            if os.path.getmtime(f) < cut or os.path.getsize(f) > 50e6:
                continue
            refs.update(canon(x) for x in PAT.findall(open(f, errors="ignore").read()))
        except OSError:
            pass
    q = os.path.join(coord, "lanes/COORD-REVIEW-QUEUE.md")
    if os.path.exists(q):
        cur = None
        for line in open(q, errors="ignore"):
            if line.startswith("- "):
                cur = line_time(line, year)
            if cur is not None and cur >= cut:
                refs.update(canon(x) for x in PAT.findall(line))
    return refs


def markers(mdir):
    ms = []
    for f in glob.glob(os.path.join(mdir, "tree_switch_*.json")):
        try:
            d = json.load(open(f)); ms.append((d.get("die", ""), d.get("tree", ""), d.get("tools_sha", ""), os.path.getmtime(f)))
        except (OSError, ValueError):
            pass
    return ms


def marker_keep(mdir):
    ms = markers(mdir); newest = {}
    for die, tree, sha, mt in ms:
        k = ALIAS.get(die, die)
        if k not in newest or mt > newest[k][3]:
            newest[k] = (die, tree, sha, mt)
    keep = {canon(t) for _, t, _, _ in newest.values() if t}
    shas = {s for _, _, s, mt in ms if s and mt == max(m[3] for m in ms)} if ms else set()
    names = [os.path.basename(t) for t in keep] + ["_pin_" + s for s in sorted(shas)]
    return keep, names


if __name__ == "__main__":
    coord, mdir, out_refs, out_keepn = sys.argv[1:5]
    hours = float(sys.argv[5]) if len(sys.argv) > 5 else 72
    refs = text_refs(coord, hours=hours); keep, names = marker_keep(mdir)
    open(out_refs, "w").write("\n".join(sorted(refs | keep)) + "\n")
    open(out_keepn, "w").write(",".join(names))
    print(len(refs), "text refs (<=%gh)," % hours, len(keep), "marker trees; keepn:", ",".join(names))
