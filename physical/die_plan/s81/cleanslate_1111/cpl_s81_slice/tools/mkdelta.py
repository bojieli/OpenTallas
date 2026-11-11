#!/usr/bin/env python3
"""CPL-S81-SLICE: per-family delta files {type: {inst: [x, y, orient]}} on plan 99f40d35071d coordinates
from fin/<type>.json, plus a family summary (bit-mm/cut/entry/rs before-after).  usage: mkdelta.py OUTDIR"""
import hashlib
import json
import os
import sys

FAM = {
    "SLICE-C": ["dsdv_slice_c1x_C__t%d" % i for i in (1, 3, 4, 5, 6, 7, 8, 9, 10)] + [
        "dsdv_slice_c3x_C__t1", "dsdv_slice_iq_C__t1", "dsdv_slice_kv512_C__t1", "dsdv_slice_lepe_mu_C__t1",
        "dsdv_slice_lepe_nh_mus_C__t1", "dsdv_slice_lepw_mu_C__t1", "dsdv_slice_lepw_mus_C__t1"],
    "SLICE-LP-W": ["dsdv_slice_lepw_mus_LP__t2", "dsdv_slice_lepw_mu_LP__t2"],
    "SLICE-LP-E": ["dsdv_slice_lepe_mu_LP__t2", "dsdv_slice_lepe_nh_mus_LP__t1"],
    "KVLEAF": ["ot_s81sl_kv_leaf__t%d" % i for i in (1, 3, 4, 5)],
}
out = sys.argv[1]
DROP = set(os.environ.get("DROP", "").split())
os.makedirs(out, exist_ok=True)
summ = {}
seen = set()
for fam, types in FAM.items():
    d, rows = {}, {}
    for t in types:
        assert t not in seen, t
        seen.add(t)
        r = json.load(open(os.path.join(os.environ.get("FIN", "fin"), "%s.json" % t)))
        if t in DROP:     # G0 gate: new G0/G0C findings naming the type -> KEEP (no delta)
            r = dict(r, delta={}, after=None, pick=None)
        if r["delta"]:
            d[t] = r["delta"]
        b, a = r["before"], r["after"]
        rows[t] = dict(pick=r["pick"], moved=len(r["delta"]), before={k: b[k] for k in ("bitmm", "cutV", "cutH", "entry", "rs_p99")},
                       after={k: a[k] for k in ("bitmm", "cutV", "cutH", "entry", "rs_p99")} if a else None)
    p = os.path.join(out, "delta_%s_99f40d35.json" % fam)
    txt = json.dumps(d, indent=1, sort_keys=True) + "\n"
    open(p, "w").write(txt)
    sha = hashlib.sha256(txt.encode()).hexdigest()
    bm0 = sum(rows[t]["before"]["bitmm"] for t in types)
    bm1 = sum((rows[t]["after"] or rows[t]["before"])["bitmm"] for t in types)
    wc0 = max(max(rows[t]["before"]["cutV"], rows[t]["before"]["cutH"]) for t in types)
    wc1 = max(max((rows[t]["after"] or rows[t]["before"])["cutV"], (rows[t]["after"] or rows[t]["before"])["cutH"]) for t in types)
    summ[fam] = dict(path=p, sha256=sha, types=types, adopted=sorted(d), bitmm_before=round(bm0), bitmm_after=round(bm1),
                     worst_cut_before=wc0, worst_cut_after=wc1, rows=rows)
    print(fam, sha[:12], "types", len(types), "adopted", len(d), "bitmm %d->%d" % (bm0, bm1), "worst cut %.3f->%.3f" % (wc0, wc1))
json.dump(summ, open(os.path.join(out, "summary.json"), "w"), indent=1)
