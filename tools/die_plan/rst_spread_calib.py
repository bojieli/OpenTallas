#!/usr/bin/env python3
"""rst_spread_calib.py -- calibration of ADV-RSTSPREAD (and RSTREACH) against retained CTS / GRT reports (C-RST-RELAY-REACH r3).

Two steps, both read-only.
  parse   reads report paths on stdin (4_cts_final.rpt, 5_*grt*.rpt kept by the kit flow), writes one TSV row per report:
            path, die, type, kind, mtime, worst recovery slack, worst removal slack, max fanout on the recovery path, startpoint, endpoint
          (type = the items/<type>/ or gen/<type>/ path segment; only the first 1,800 lines are read, where the path groups are)
  score   RSTSPREAD feature json files (adv_rst_spread.py --json) x report TSVs -> TP / FP / FN per die and label.
          Label per type = the WORST report of that type name (min over reports): REC = recovery < 0, ANY = recovery < 0 or removal < 0.
          Rule = the plan_advisory defaults (max fanout > 3000, seat-to-tap > 405 um, HPWL > 900 um) or --rule fanout=..,far=..,hpwl=..
          --rstreach FILE (comma list of types RSTREACH FAILs) prints the RSTREACH-only recall and the union recall.

    find <kit dirs> -name 4_cts_final.rpt -o -name '5_*grt*.rpt' | rst_spread_calib.py parse > rpt.tsv
    rst_spread_calib.py score --rpt rpt.tsv [--rpt ...] --die s81=s81_spread.json --die kv=kv_spread.json [--rstreach s81=types.txt]
Caveat printed with the result: report forms are older than the plan the features are computed on (a type name is the join key), and
most retained kit reports fail removal, so a high-fanout flag has a high base rate on the ANY label; read lift, not just precision.
"""
import argparse
import itertools
import json
import os
import re
import sys

NUM = r"[-+]?\d+(?:\.\d+)?"


def parse_report(p):
    rec = rem = None
    recfo = 0
    sp = ep = ""
    blk = []
    best = {}

    def flush():
        nonlocal rec, rem, recfo, sp, ep
        if not blk:
            return
        kind = slack = None
        fo = 0
        s = e = ""
        for ln in blk:
            if ln.startswith("Startpoint:"):
                s = ln.split()[1]
            elif ln.startswith("Endpoint:"):
                e = ln.split()[1]
            elif "recovery check against" in ln:
                kind = "rec"
            elif "removal check against" in ln:
                kind = "rem"
            elif "slack (" in ln:
                try:
                    slack = float(ln.split()[0])
                except ValueError:
                    pass
            else:
                m = re.match(r"\s+(\d+)\s+" + NUM + r"\s+" + NUM + r"\s+" + NUM + r"\s+" + NUM + r"\s+[\^v]\s", ln)
                if m:
                    fo = max(fo, int(m.group(1)))
        if kind and slack is not None:
            if kind == "rec" and (rec is None or slack < rec):
                rec, recfo, sp, ep = slack, fo, s, e
            if kind == "rem" and (rem is None or slack < rem):
                rem = slack
    try:
        f = open(p, errors="replace")
    except OSError:
        return None
    with f:
        for ln in itertools.islice(f, 1800):
            if ln.startswith("Startpoint:"):
                flush()
                blk = [ln]
            elif blk:
                blk.append(ln)
    flush()
    return rec, rem, recfo, sp, ep


def report_type(p):
    m = re.search(r"/items/([^/]+)/", p) or re.search(r"/gen/([^/]+)/", p) or re.search(r"/(?:dp_|)([^/]+)/base/", p)
    return m.group(1) if m else ""


def cmd_parse(_a):
    for p in sys.stdin:
        p = p.strip()
        r = parse_report(p) if p else None
        if r is None:
            continue
        d = re.search(r"/runs/([^/]+)/", p)
        try:
            mt = int(os.path.getmtime(p))
        except OSError:
            mt = 0
        kind = "cts" if "cts" in p.rsplit("/", 1)[1] else "grt"
        rec, rem, fo, sp, ep = r
        print("\t".join(str(x) for x in (p, d.group(1) if d else "", report_type(p), kind, mt,
                                          "" if rec is None else rec, "" if rem is None else rem, fo, sp, ep)))
    return 0


def labels(paths):
    L = {}
    for f in paths:
        for ln in open(f):
            a = ln.rstrip("\n").split("\t")
            if len(a) < 8:
                continue
            try:
                rec = float(a[5]) if a[5] else None
                rem = float(a[6]) if a[6] else None
            except ValueError:
                continue
            if rec is None and rem is None:
                continue
            d = L.setdefault(a[2], dict(rec=None, rem=None, n=0))
            d["n"] += 1
            if rec is not None and (d["rec"] is None or rec < d["rec"]):
                d["rec"] = rec
            if rem is not None and (d["rem"] is None or rem < d["rem"]):
                d["rem"] = rem
    return L


def positive(l, what):
    r, m = l["rec"], l["rem"]
    return (r is not None and r < 0) if what == "rec" else ((r is not None and r < 0) or (m is not None and m < 0))


def flagged(f, rule):
    return f["max_fanout"] > rule["fanout"] or f["far"] > rule["far"] or f["max_hpwl"] > rule["hpwl"]


def tally(rows, pred, what):
    tp = fp = fn = tn = 0
    for _tn, f, l in rows:
        y, p = positive(l, what), pred(_tn, f)
        tp += p and y
        fp += p and not y
        fn += (not p) and y
        tn += (not p) and not y
    return tp, fp, fn, tn


def cmd_score(a):
    L = labels(a.rpt)
    rule = dict(fanout=3000, far=405.0, hpwl=900.0)
    for kv in (a.rule or "").split(","):
        if "=" in kv:
            k, v = kv.split("=")
            rule[k] = float(v)
    rs = {}
    for x in a.rstreach or []:
        d, f = x.split("=")
        rs[d] = set(filter(None, open(f).read().replace("\n", ",").split(",")))
    print(f"retained reports with recovery/removal data: {sum(v['n'] for v in L.values())} over {len(L)} type names; rule {rule}")
    tot = {w: [0, 0, 0, 0] for w in ("rec", "any")}
    for x in a.die:
        die, f = x.split("=")
        F = json.load(open(f))["types"]
        rows = [(tn, F[tn], L[tn]) for tn in F if tn in L]
        print(f"{die}: {len(F)} plan types, {len(rows)} with a retained report, flagged {sum(flagged(r[1], rule) for r in rows)}")
        for what in ("rec", "any"):
            t = tally(rows, lambda tn, ft: flagged(ft, rule), what)
            for i in range(4):
                tot[what][i] += t[i]
            pos = t[0] + t[2]
            print(f"  RSTSPREAD {what}<0: TP {t[0]} FP {t[1]} FN {t[2]} TN {t[3]}  recall {t[0] / pos:.2f}" if pos else f"  RSTSPREAD {what}: no positives")
            if die in rs:
                r1 = tally(rows, lambda tn, ft: tn in rs[die], what)
                r2 = tally(rows, lambda tn, ft: tn in rs[die] or flagged(ft, rule), what)
                print(f"  RSTREACH only {what}: TP {r1[0]} FP {r1[1]} FN {r1[2]} recall {r1[0] / pos:.2f}; union TP {r2[0]} FP {r2[1]} FN {r2[2]} "
                      f"recall {r2[0] / pos:.2f}")
    for what in ("rec", "any"):
        t = tot[what]
        pos = t[0] + t[2]
        if pos:
            print(f"ALL dies RSTSPREAD {what}<0: TP {t[0]} FP {t[1]} FN {t[2]} TN {t[3]}  recall {t[0] / pos:.2f}  precision "
                  f"{(t[0] / (t[0] + t[1]) if t[0] + t[1] else 0):.2f}  base rate {pos / sum(t):.2f}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("parse")
    s = sub.add_parser("score")
    s.add_argument("--rpt", action="append", required=True)
    s.add_argument("--die", action="append", required=True)
    s.add_argument("--rstreach", action="append")
    s.add_argument("--rule")
    a = ap.parse_args(argv)
    return cmd_parse(a) if a.cmd == "parse" else cmd_score(a)


if __name__ == "__main__":
    sys.exit(main())
