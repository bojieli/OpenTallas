#!/usr/bin/python3 -I
"""SCHED-1 11-07, OWNER closure first: lanes/NEAR-CLOSE.tsv = jobs one bounded step from sign-off (one net, a few slews, a
re-sign, routed LEC).  Refreshes the 'miss' column of each row from its sign-off JSON and appends new near misses found in
sign-off JSONs of the last --hours.  Die owners keep next_step, owner and path by hand; rows are never deleted here
(an owner deletes a row when it is counted).  Read-only on the fleet.  Usage: near_close.py [--hours 3] [--write] [--commit]"""
import argparse, concurrent.futures as cf, json, os, re, subprocess, sys, time
HOSTS = ["intel1", "intel2", "epyc2", "epyc4", "epyc5", "epyc6", "epyc7", "epyc8", "epyc9"]
COLS = ["die", "block", "host", "path", "miss", "next_step", "owner", "updated"]
TSV = os.path.expanduser("~/coord/lanes/NEAR-CLOSE.tsv")
HEAD = ("# NEAR-CLOSE (SCHED-1 2026-11-07, OWNER closure first). One bounded step from sign-off. New "
        "builds do not. Non-AUTO rows are the critical set for ot-run-direct --direct (immediate start); keep it small. Die owners own the fixes: edit next_step/owner/path, delete a row once counted. miss/updated are rewritten "
        "hourly from path/signoff/signoff.json by bin/near_close.py; AUTO rows are scan finds an owner has not confirmed.\n")
# one remote program: path list on stdin (or scan) -> one JSON summary per line
REMOTE = r'''
import glob, json, os, re, subprocess, sys, time
def lec(k):
    b = []
    for pat in ("lec.json", "lec/lec.json", "lec_postroute*/lec.json", "signoff/lec.json"):
        b += glob.glob(os.path.join(k, pat))
    if not b:
        return "none"
    try:
        d = json.load(open(max(b, key=os.path.getmtime)))
        return str(d.get("verdict") or d.get("status") or d.get("result") or "?")
    except Exception:
        return "?"
def one(p):
    k = os.path.dirname(os.path.dirname(p))
    try:
        d = json.load(open(p))
    except Exception:
        return None
    c = d.get("checks") or {}
    n = lambda key, f="violators": (c.get(key) or {}).get(f)
    row = dict(p=k, name=d.get("name"), verdict=d.get("verdict"), reasons=(d.get("reasons") or [])[:4], m=int(os.path.getmtime(p)),
               tt=n("setup_tt", "wns_ps"), ttn=n("setup_tt"), ff=n("hold_ff", "wns_ps"), ffn=n("hold_ff"), lec=lec(k),
               drc=(d.get("route") or {}).get("drc"), checks={x: {y: z for y, z in v.items() if isinstance(z, (int, float, str))}
                     for x, v in c.items() if isinstance(v, dict) and x not in ("setup_tt", "hold_ff")})
    return row
a = sys.argv[1:]
ps = []
if a and a[0] == "scan":
    roots = [r + "/claude" for r in ("/srv/opentallas-scratch", "/srv/opentallas-scratch2", "/srv/opentallas-scratch3") if os.path.isdir(r + "/claude")]
    x = subprocess.run(["nice", "-n19", "ionice", "-c3", "timeout", "240", "find"] + roots + ["-maxdepth", "9", "-name", "signoff.json", "-path", "*/signoff/*",
        "-mmin", "-" + a[1], "-not", "-path", "*/wt/*"], capture_output=True, text=True).stdout
    ps = x.split()
else:
    ps = [os.path.join(k, "signoff/signoff.json") for k in a if os.path.isfile(os.path.join(k, "signoff/signoff.json"))]
for p in ps:
    r = one(p)
    if r:
        print(json.dumps(r))
'''
def remote(host, args, timeout=300):
    r = subprocess.run(["ssh", "-n", "-o", "ControlPath=none", "-o", "ConnectTimeout=20", host, "python3 -I -c " + shq(REMOTE) + " " + " ".join(shq(a) for a in args)], capture_output=True, text=True, timeout=timeout)
    out = []
    for ln in r.stdout.splitlines():
        try:
            out.append(json.loads(ln))
        except ValueError:
            pass
    return out
def shq(s):
    return "'" + s.replace("'", "'\\''") + "'"
def count(c, key):
    v = c.get(key) or {}
    for f in ("violators", "count", "n", "max_slew_violations", "violations"):
        if isinstance(v.get(f), (int, float)):
            return int(v[f])
    return None
def miss(r):
    c = r.get("checks") or {}
    extra = []
    for k, v in sorted(c.items()):
        if v.get("verdict") not in (None, "PASS", "pass", "N/A", "NA", "SKIP"):
            n = count(c, k)
            extra.append(f"{k}{'' if n is None else ' ' + str(n)}")
    age = (time.time() - r.get("m", 0)) / 3600
    tt, ff = r.get("tt"), r.get("ff")
    return (f"{r.get('verdict')} TT {tt} FF {ff} DRC {r.get('drc')} LEC {r.get('lec')}"
            + (" fails: " + ",".join(extra) if extra else "") + f" ({age:.1f} h old)")
def near(r):
    """one bounded step: TT within -5 ps, FF within -12 ps (or port-only), few electrical rows, at most 2 DRC"""
    if "/results/" in r.get("p", "") or "NEEDS_PARENT" in str(r.get("verdict")):
        return False                                            # a source copy of a view; NEEDS_PARENT already counts
    if r.get("verdict") == "SIGNED":
        return r.get("lec") not in ("EQUIVALENT",)              # signed, routed LEC / re-sign owed
    tt, ff, drc = r.get("tt"), r.get("ff"), r.get("drc") or 0
    if tt is None or ff is None or tt < -5 or ff < -12 or drc > 2:
        return False
    c = r.get("checks") or {}
    bad = sum(count(c, k) or 0 for k, v in c.items() if "slew" in k or "cap" in k or "drv" in k.lower())
    return bad <= 12
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=3)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--commit", action="store_true")
    a = ap.parse_args()
    head, rows = HEAD, []
    if os.path.exists(TSV):
        for ln in open(TSV):
            if ln.startswith("#") or ln.startswith("die\t") or not ln.strip():
                continue
            v = ln.rstrip("\n").split("\t")
            rows.append(dict(zip(COLS, v + [""] * (len(COLS) - len(v)))))
    now = time.strftime("%m-%d %H:%M")
    by = {}
    for r in rows:
        by.setdefault(r["host"], []).append(r)
    def work(h):
        return h, remote(h, [r["path"] for r in by.get(h, []) if r["path"].startswith("/")]) if by.get(h) else [], remote(h, ["scan", str(int(a.hours * 60))])
    known = {(r["host"], r["path"]) for r in rows}
    names = {r["block"] for r in rows}
    with cf.ThreadPoolExecutor(len(HOSTS)) as x:
        for h, cur, scan in x.map(work, HOSTS):
            cm = {s["p"]: s for s in cur}
            for r in by.get(h, []):
                if r["path"] in cm:
                    r["miss"], r["updated"] = miss(cm[r["path"]]), now
            for s in scan:
                if near(s) and (h, s["p"]) not in known and str(s.get("name")) not in names:
                    known.add((h, s["p"]))
                    names.add(str(s.get("name")))
                    rows.append(dict(die="?", block=str(s.get("name")), host=h, path=s["p"], miss=miss(s),
                                     next_step="AUTO: scan find, owner to confirm or delete", owner="die owner", updated=now))
    text = head + "\t".join(COLS) + "\n" + "".join("\t".join(r[c] for c in COLS) + "\n" for r in rows)
    if not a.write:
        sys.stdout.write(text)
        return
    tmp = TSV + ".tmp"
    open(tmp, "w").write(text)
    os.replace(tmp, TSV)
    if a.commit:
        subprocess.run(["timeout", "280", os.path.expanduser("~/coord/bin/coord-commit.sh"), "NEAR-CLOSE refresh", "lanes/NEAR-CLOSE.tsv"])
main()
