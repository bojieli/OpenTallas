#!/usr/bin/env python3
"""QC-ALLFIX-TSV ledger_vs_plan.py: check every ALLFIX-QC.tsv row that claims to be in the plan against the PLAN CONTENT.
usage: ledger_vs_plan.py --plan PLAN.json --tsv ALLFIX-QC.tsv --manifest MANIFEST.json [--json OUT.json]
Run at every cut (COORD 11-25 04:4x, after STB ring row 44a145a65013 was ledger-STAGED but never in C1n/C1o).
MANIFEST: {"plans": {name: path}, "rowchk": path, "rows": [{"item": TSV item prefix, "kind": ..., ...}]}
  kind file   base,row      plan pair: every flattened key the row changed vs base (rowstat/QC-COMPOSE-GUARD flatten)
  kind step   frm,to,rx,nrx compose step delta filtered by regex (plans by name)
  kind rowchk key           precomputed path/base/row list (rows_vs_c1k.json)
  kind set    file          [{"path": dotted, "new": v}] (RRDRV style)
  kind jsonpatch file       {"ops": [{"path": "/a/b", "value": v}]}
  kind seatset file         {"set": [{"path": "partition_types.T.relay_sites.KEY", "old", "new"}]}
  kind files  files         [{"rel", "sha12"}] under --tree (RTL overlay / launch-tree file rows)
  kind keys   keys,source    [{"path", "value"}] exact values from the originating post when no row file is left
  kind visrow file          VIS-QC row json (changed_paths + partition_types)
  kind prune  file          {"types": {t: {"remove_relay_sites": [k]}}}: keys must be absent
  kind notplan note         no plan delta (sidecar / launch-tree file / tool): listed, not judged
Per key: CARRIED (row value), REPLACED (a third value: later row), LOST (base value: row not applied), ABSENT (key gone),
A LOST/ABSENT key whose plan value equals what another manifest row set there counts as REPLACED (superseded_by).
DROP-DECLARED (ABSENT/LOST but matched by a --drop-list line = removal declared at a gate; counts as present).
Row verdict: PRESENT (LOST+ABSENT=0), ABSENT (CARRIED+REPLACED=0), else PARTIAL (n/m present).
Checked TSV rows: status starts IN / STAGED / PENDING / READY / BOUND / KIT / COMPOSED (not DEFERRED/SUPERSEDED/RETIRED).
DEFERRED rows with a manifest source are judged too and printed as DEFERRED/<verdict> (never fail).
--posts adds the RC-QC-39 report-only C1p check (ALLFIX row + owner post < 3 h); it never changes rc.
rc 1 when a checked row is ABSENT or PARTIAL or has no manifest source (NO-SOURCE); DEFERRED rows never fail."""
import argparse, csv, gc, hashlib, json, re, sys
from collections import Counter

ap = argparse.ArgumentParser()
ap.add_argument("--plan", required=True); ap.add_argument("--tsv", required=True)
ap.add_argument("--manifest", required=True); ap.add_argument("--json")
ap.add_argument("--drop-list", action="append", default=[], help="guard-format drop lists ('[KIND ]fnmatch # reason'); "
                "an ABSENT/LOST key matching one counts as DROP-DECLARED (an intended removal recorded at a gate)")
ap.add_argument("--posts", help="hub lanes/posts dir: enables the RC-QC-39 report-only check (C1p rows need an ALLFIX row + owner post < 3 h)")
ap.add_argument("--compose-list", help="optional C1p compose list (TSV: row<TAB>owner); without it the TSV's own C1p rows are used")
ap.add_argument("--now", help="'YYYY-MM-DD HH:MM' PST for the post-age check (default: now, America/Los_Angeles)")
ap.add_argument("--tree", help="launch tree root for kind files (RTL overlays, launch-tree files)")
a = ap.parse_args()

def md5(x): return hashlib.md5(json.dumps(x, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:10]
def flat(node, pre, depth, out):
    if isinstance(node, dict) and depth > 0 and node:
        for k, v in node.items(): flat(v, pre + (k,), depth - 1, out)
    else: out[".".join(pre)] = md5(node)
def flatten(P):
    out = {}
    for k, v in P.items():
        if k == "partition_types":
            for t, tv in v.items(): flat(tv, ("partition_types", t), 2, out)
        else: flat(v, (k,), 3, out)
    return out
TOK = re.compile(r"([^.\[\]]+)|\[(\d+)\]|\[(\w+)=([^\]]+)\]")
def resolve(P, path):
    """dotted (a.b[0].c[name=x]) or JSON pointer (/a/b/0); returns (found, value)."""
    toks = [int(x) if x.isdigit() else x for x in path.strip("/").split("/")] if path.startswith("/") else None
    cur = P
    if toks is None:
        toks = []
        for m in TOK.finditer(path):
            toks.append(m.group(1) if m.group(1) is not None else int(m.group(2)) if m.group(2) is not None else (m.group(3), m.group(4)))
    for t in toks:
        try:
            if isinstance(t, tuple):
                c = [x for x in cur if isinstance(x, dict) and str(x.get(t[0])) == t[1]]
                if len(c) != 1: return False, None
                cur = c[0]
            else: cur = cur[t]
        except (KeyError, IndexError, TypeError): return False, None
    return True, cur

M = json.load(open(a.manifest)); plans = M.get("plans", {})
import os
_need = set(plans.values()) | ({M["rowchk"]} if M.get("rowchk") else set())
for _r in M["rows"]:
    _need |= {_r[k] for k in ("base", "row", "file") if _r.get(k)}
_miss = sorted(p for p in _need if not os.path.exists(p))
if _miss:
    print("LEDGER-VS-PLAN MISSING-SOURCE-FILES", _miss); sys.exit(2)
rawplan = json.load(open(a.plan)); T = flatten(rawplan)
cache = {}
def fl(p):
    if p not in cache:
        cache[p] = flatten(json.load(open(p))); gc.collect()
    return cache[p]

import fnmatch
DL = []
for _f in a.drop_list:
    for _l in open(_f):
        _l = _l.split(" # ")[0].strip()
        if not _l or _l.startswith("#"): continue
        _p = _l.split(None, 1)
        if len(_p) == 2 and _p[0].isupper() and "." not in _p[0]: _l = _p[1]
        DL.append(_l)
_DLX = re.compile("|".join(fnmatch.translate(x) for x in DL)) if DL else None
def declared(path):
    return bool(_DLX and _DLX.match(path))

ROWVAL = {}   # flat path -> {(item, row md5)}: lets a LOST/ABSENT key be traced to the later row that set the plan's value
def judge_flat(entries):
    c = Counter(); ex = {}
    for path, bv, rv in entries:
        ROWVAL.setdefault(path, set()).add((CUR[0], rv))
        tv = T.get(path)
        if tv == rv: s = "CARRIED"
        elif tv is None: s = "ABSENT"
        elif bv is not None and tv == bv: s = "LOST"
        else: s = "REPLACED"
        if s in ("ABSENT", "LOST") and declared(path): s = "DROP-DECLARED"
        c[s] += 1; ex.setdefault(s, path)
        if s in ("ABSENT", "LOST"): BADP.setdefault(CUR[0], []).append((s, path))
    return c, ex

def run(row):
    try:
        return _run(row)
    except Exception as e:   # a broken source never crashes the cut; it is reported and fails it
        return Counter({"ERROR": 1}), {"ERROR": "%s: %s" % (type(e).__name__, e)}, ""

def _run(row):
    k = row["kind"]
    if k == "notplan": return None, {}, row.get("note", "")
    if k in ("file", "step"):
        A, B = (fl(row["base"]), fl(row["row"])) if k == "file" else (fl(plans[row["frm"]]), fl(plans[row["to"]]))
        rx = re.compile(row.get("rx") or "."); nrx = re.compile(row["nrx"]) if row.get("nrx") else None
        ent = [(p, A.get(p), B.get(p)) for p in set(A) | set(B)
               if A.get(p) != B.get(p) and rx.search(p) and not (nrx and nrx.search(p))]
        if k == "file" and row.get("drop_cache"): cache.pop(row["row"], None); gc.collect()
        return judge_flat(ent) + ("",)
    if k == "rowchk":
        if "rc" not in cache: cache["rc"] = json.load(open(M["rowchk"]))
        ent = [(e["path"], e["base"][0] if e["base"] else None, e["row"][0] if e["row"] else None) for e in cache["rc"][row["key"]]]
        return judge_flat(ent) + ("",)
    c = Counter(); ex = {}
    r = json.load(open(row["file"])) if row.get("file") else {}
    if k == "set":
        items = [(e["path"], e.get("old"), e["new"]) for e in r["set"]]
    elif k == "jsonpatch":
        items = [(o["path"], o.get("old"), o["value"] if o.get("op") != "remove" else ("ABSENT-PATH",)) for o in r["ops"]]
    elif k == "seatset":   # relay_sites keys may contain dots/brackets: partition_types.T.relay_sites.KEY
        items = [(e["path"], e.get("old"), e["new"]) for e in r["set"]]
    elif k == "files":     # [{"rel": path under --tree, "sha12": ...}]: overlay/launch-tree files must match by content
        import hashlib as _h, os as _os
        for e in row["files"]:
            p = _os.path.join(a.tree or "", e["rel"])
            if not a.tree or not _os.path.exists(p): c["ABSENT"] += 1; ex.setdefault("ABSENT", e["rel"]); continue
            got = _h.sha256(open(p, "rb").read()).hexdigest()[:12]
            s_ = "CARRIED" if got == e["sha12"] else "LOST"; c[s_] += 1; ex.setdefault(s_, e["rel"])
        return c, ex, ""
    elif k == "keys":      # exact path/value pairs taken from the originating post (row file gone); "source" cites it
        items = [(e["path"], e.get("old"), e["value"]) for e in (row.get("keys") or r["keys"])]
    elif k == "visrow":    # VIS-QC row json: changed_paths {T: ["T.k1.k2 SET"]}, values from its partition_types
        items = []
        for t, lst in r["changed_paths"].items():
            for s_ in lst:
                ks = s_.rsplit(" ", 1)[0].split(".")[1:]; v = r["partition_types"][t]
                for kk in ks: v = v[kk]
                items.append(("partition_types.%s.%s" % (t, ".".join(ks)), None, v))
    elif k == "prune":
        items = [("partition_types.%s.relay_sites" % t, None, ("ABSENT-KEY", kk)) for t, v in r["types"].items() for kk in v["remove_relay_sites"]]
    for path, old, new in items:
        if k == "prune":
            f, cur = resolve(rawplan, path); s = "CARRIED" if not (f and new[1] in (cur or {})) else "LOST"
        elif k == "seatset":
            _, t, _, kk = path.split(".", 3); rs = rawplan["partition_types"].get(t, {}).get("relay_sites", {})
            f, cur = kk in rs, rs.get(kk)
            s = "CARRIED" if f and cur == new else "ABSENT" if not f else "LOST" if old is not None and cur == old else "REPLACED"
        elif new == ("ABSENT-PATH",):   # jsonpatch remove: the path must be gone
            f, cur = resolve(rawplan, path); s = "LOST" if f else "CARRIED"
        else:
            f, cur = resolve(rawplan, path)
            s = "CARRIED" if f and cur == new else "ABSENT" if not f else "LOST" if old is not None and cur == old else "REPLACED"
        c[s] += 1; ex.setdefault(s, path)
    return c, ex, ""

BADP = {}; CUR = [None]
CHECK = re.compile(r"^(IN|STAGED|PENDING|READY|BOUND|KIT|COMPOSED)")
byitem = {}
for row in M["rows"]: byitem.setdefault(row["item"], []).append(row)
out = []; bad = 0
with open(a.tsv) as f:
    rd = csv.reader(f, delimiter="\t"); hdr = next(rd)
    while hdr and hdr[0].startswith("#"): hdr = next(rd)
    si = hdr.index("status")
    for r in rd:
        if not r or r[0].startswith("#"): continue
        item, st = r[0], r[si]
        srcs = [v for kk, vv in byitem.items() if item.startswith(kk) for v in vv]
        deferred = st.startswith("DEFERRED"); CUR[0] = item
        if deferred and srcs:   # informational: a deferred row with a source is judged but never fails the cut
            tot = Counter()
            for s in srcs:
                c, ex, note = run(s)
                if c: tot.update(c)
            if tot:
                m = sum(tot.values()); pres = tot["CARRIED"] + tot["REPLACED"] + tot["DROP-DECLARED"]
                v = "ERROR" if tot["ERROR"] else "PRESENT" if tot["LOST"] + tot["ABSENT"] == 0 else "ABSENT" if pres == 0 else "PARTIAL %d/%d" % (pres, m)
                out.append(dict(item=item, status=st, verdict="DEFERRED/" + v, counts=dict(tot)))
            continue
        if not CHECK.search(st): continue
        if not srcs:
            out.append(dict(item=item, status=st, verdict="NO-SOURCE", detail="no manifest entry")); bad += 1; continue
        tot = Counter(); exs = {}; notes = []
        CUR[0] = item
        for s in srcs:
            c, ex, note = run(s)
            if c is None: notes.append(note); continue
            tot.update(c); exs.update({kk: vv for kk, vv in ex.items() if kk not in exs})
        if not tot:
            out.append(dict(item=item, status=st, verdict="NOTPLAN", detail="; ".join(notes))); continue
        m = sum(tot.values()); pres = tot["CARRIED"] + tot["REPLACED"] + tot["DROP-DECLARED"]
        v = "ERROR" if tot["ERROR"] else "PRESENT" if tot["LOST"] + tot["ABSENT"] == 0 else "ABSENT" if pres == 0 else "PARTIAL %d/%d" % (pres, m)
        if v != "PRESENT": bad += 1
        out.append(dict(item=item, status=st, verdict=v, counts=dict(tot), example=exs))
# second pass: a LOST/ABSENT key whose plan value is exactly what ANOTHER manifest row set there was superseded by that row
for o in out:
    bp = BADP.get(o["item"]) or []
    if not bp or "counts" not in o: continue
    c = Counter(o["counts"]); by = Counter()
    for s_, p in bp:
        tv = T.get(p)
        hit = sorted({it for it, rv in ROWVAL.get(p, ()) if it != o["item"] and rv == tv})
        if hit:
            c[s_] -= 1; c["REPLACED"] += 1; by[hit[0][:40]] += 1
    if by:
        o["counts"] = {k: v for k, v in c.items() if v}; o["superseded_by"] = dict(by)
        m = sum(c.values()); pres = c["CARRIED"] + c["REPLACED"] + c["DROP-DECLARED"]
        v = "ERROR" if c["ERROR"] else "PRESENT" if c["LOST"] + c["ABSENT"] == 0 else "ABSENT" if pres == 0 else "PARTIAL %d/%d" % (pres, m)
        pre = "DEFERRED/" if o["verdict"].startswith("DEFERRED/") else ""
        if not pre and o["verdict"] != "PRESENT" and v == "PRESENT": bad -= 1
        o["verdict"] = pre + v
for o in out:
    print("%-14s %-60s %s %s %s" % (o["verdict"], o["item"][:60], o.get("counts", o.get("detail", "")), {k: v for k, v in o.get("example", {}).items() if k in ("LOST", "ABSENT", "ERROR")}, ("superseded_by " + str(o["superseded_by"])) if o.get("superseded_by") else ""))
print("LEDGER-VS-PLAN", Counter(o["verdict"].split()[0] for o in out), "plan", a.plan, hashlib.sha256(open(a.plan, "rb").read()).hexdigest()[:12])
print("LEDGER-VS-PLAN", "PASS" if bad == 0 else "FAIL %d" % bad)
# RC-QC-39 (FABLE-RC-QC 11-25 07:5x) report-only: every C1p row needs an ALLFIX-QC row and an owner post < 3 h old
c1p_report = []
if a.posts:
    import datetime as _dt, os as _os, pathlib as _pl
    try:
        from zoneinfo import ZoneInfo as _Z
        now = _dt.datetime.strptime(a.now, "%Y-%m-%d %H:%M") if a.now else _dt.datetime.now(_Z("America/Los_Angeles")).replace(tzinfo=None)
    except Exception:
        now = _dt.datetime.strptime(a.now, "%Y-%m-%d %H:%M") if a.now else _dt.datetime.now()
    PAT = re.compile(r"^- (\d{4}-\d\d-\d\d \d\d:\d\d) PST")
    def last_post(lane):
        best = None
        for md in _pl.Path(a.posts).glob("*.md"):
            for line in md.read_text(errors="replace").splitlines():
                mm = PAT.match(line)
                if mm and ("[%s " % lane in line or "[%s]" % lane in line or "[%s ->" % lane in line or (md.stem == lane)):
                    t = mm.group(1); best = t if best is None or t > best else best
        return best
    tsv_rows = []
    with open(a.tsv) as f:
        rd = csv.reader(f, delimiter="\t"); h = next(rd); si2 = h.index("status")
        tsv_rows = [(r[0], r[si2]) for r in rd if r]
    want = []
    if a.compose_list:
        for l in open(a.compose_list):
            p = l.rstrip("\n").split("\t")
            if p and p[0] and not p[0].startswith("#"): want.append((p[0], p[1] if len(p) > 1 else ""))
    else:
        for it, st in tsv_rows:
            if "C1p" in st:
                mo = re.search(r"owner ([A-Z0-9][A-Za-z0-9-]+)", st); want.append((it, mo.group(1) if mo else ""))
    for row, owner in want:
        has = any(row[:30] in it or it.startswith(row[:30]) for it, _ in tsv_rows)
        lp = last_post(owner) if owner else None
        age = (now - _dt.datetime.strptime(lp, "%Y-%m-%d %H:%M")).total_seconds() / 3600 if lp else None
        flag = [] if has else ["NO-ALLFIX-ROW"]
        if not owner: flag.append("NO-OWNER")
        elif age is None: flag.append("NO-OWNER-POST")
        elif age >= 3: flag.append("STALE-OWNER %.1fh" % age)
        c1p_report.append(dict(row=row, owner=owner, last_post=lp, age_h=None if age is None else round(age, 1), flags=flag))
    nflag = sum(1 for x in c1p_report if x["flags"])
    for x in c1p_report:
        if x["flags"]: print("C1P-CHECK %-50s owner=%-22s last=%s %s" % (x["row"][:50], x["owner"], x["last_post"], ",".join(x["flags"])))
    print("C1P-CHECK (report-only) rows %d flagged %d" % (len(c1p_report), nflag))
if a.json: json.dump(dict(rows=out, bad_paths=BADP, c1p_report=c1p_report), open(a.json, "w"), indent=1)
sys.exit(1 if bad else 0)
