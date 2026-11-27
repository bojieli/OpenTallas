#!/usr/bin/env python3
"""rst_spread_placed_calib.py -- calibration of rst_spread_placed.py against retained CTS reports (C-RST-PLACED, CLASS-OWNERS-R2).
    batch : stdin lines "geom.tsv<TAB>4_cts_final.rpt" -> one JSON line per kit (flagged nets, worst recovery / removal slack)
    score : python3 rst_spread_placed_calib.py score RES.jsonl... -> TP/FP/FN/TN per die for the REC<0 and ANY<0 labels
Labels: REC = worst recovery slack < 0 in 4_cts_final.rpt; ANY = recovery or removal < 0.  Rule = any reset net flagged."""
import json
import os
import re
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rst_spread_placed as R
from multiprocessing import Pool
NUM = r"[-+]?\d+(?:\.\d+)?"
def cts(p):
    rec = rem = None; kind = None; slack = None
    n = 0
    try:
        f = open(p, errors="replace")
    except OSError:
        return None, None
    for ln in f:
        n += 1
        if n > 6000: break
        if "recovery check against" in ln: kind = "rec"
        elif "removal check against" in ln: kind = "rem"
        elif ln.startswith("Startpoint:"): kind = None
        elif "slack (" in ln and kind:
            try: v = float(ln.split()[0])
            except ValueError: kind = None; continue
            if kind == "rec": rec = v if rec is None else min(rec, v)
            else: rem = v if rem is None else min(rem, v)
            kind = None
    return rec, rem
def score_main(files):
    import collections, glob
    rows = []
    for f in files:
        for l in open(f):
            try:
                rows.append(json.loads(l))
            except ValueError:
                pass
    def die(g):
        m = re.search(r"/runs/([^/]+)/", g)
        return {"s81": "S81", "qwen_kvsys": "KV", "qwen_compute": "QC", "s81_head": "HEAD"}.get(m.group(1), "?") if m else "?"
    labels = (("REC<0", lambda r: r["rec"] is not None and r["rec"] < 0),
              ("ANY<0", lambda r: (r["rec"] is not None and r["rec"] < 0) or (r["rem"] is not None and r["rem"] < 0)))
    for nm, lab in labels:
        print(nm)
        t = collections.defaultdict(collections.Counter)
        for r in rows:
            if "err" in r or (r["rec"] is None and r["rem"] is None):
                continue
            y, x = lab(r), r["flagged"] > 0
            t[die(r["geom"])][("TP" if x else "FN") if y else ("FP" if x else "TN")] += 1
        for d, c in sorted(t.items()):
            tp, fp, fn, tn = c["TP"], c["FP"], c["FN"], c["TN"]
            print(f"  {d}: n={tp+fp+fn+tn} TP={tp} FP={fp} FN={fn} TN={tn} recall={tp/max(1,tp+fn):.2f} precision={tp/max(1,tp+fp):.2f}")


def one(line):
    g, rp = line.split("\t")[:2]
    try:
        gg, res = R.analyse(g)
    except Exception as e:
        return dict(geom=g, err=str(e)[:80])
    rec, rem = cts(rp)
    fl = [r for r in res if r["flags"]]
    mx = lambda k: max([r[k] for r in res] or [0])
    return dict(geom=g, rpt=rp, nets=len(res), flagged=len(fl), max_fanout=mx("fanout"), max_hpwl=mx("hpwl_um"), max_far=mx("far_um"),
                max_regions=mx("regions"), in_macro=sum(r["in_macro"] for r in res), rec=rec, rem=rem,
                flags=sorted({f for r in fl for f in r["flags"]}), src=sorted({r["src"] for r in res}),
                worst=[(r["net"][-60:], r["fanout"], r["hpwl_um"], r["far_um"], r["regions"], r["in_macro"]) for r in fl[:3]])
if __name__ == "__main__" and sys.argv[1:2] == ["score"]:
    score_main(sys.argv[2:])
elif __name__ == "__main__":
    lines = [l.rstrip("\n") for l in sys.stdin if l.strip()]
    with Pool(int(os.environ.get("NP", "3"))) as p:
        for o in p.imap_unordered(one, lines):
            print(json.dumps(o), flush=True)
