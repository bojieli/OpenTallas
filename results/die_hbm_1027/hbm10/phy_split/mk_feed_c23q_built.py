"""DIE-HBM-10 C23q BUILT feed: feed_c23q.tsv (estimate: W/E partitions 146.88 + 308 x 8.64 = 2808.0 um) re-scaled to the
built c23q partitions (apply_c23q.py: PHY_NW 2661.12, PHY_NC 3188.16, PHY_NE 2954.88 um) by the half-width change at the
shared wire model V = 0.3659 ps/um, as c23q.py / mk_feed_c23.py.  Feed taps unchanged.
usage: mk_feed_c23q_built.py FEED_C23Q PLAN OUT"""
import csv, json, sys
src, plan, out = sys.argv[1:4]
P = json.load(open(plan)); W = {t: P["partition_types"][t]["outline_um"][0] for t in ("PHY_NW", "PHY_NC", "PHY_NE")}
est = {"T060W": 146.88 + 308 * 8.64, "T060C": 369 * 8.64, "T060E": 146.88 + 308 * 8.64}
built = {"T060W": W["PHY_NW"], "T060C": W["PHY_NC"], "T060E": W["PHY_NE"]}
F = list(csv.DictReader(open(src), delimiter="\t"))
for r in F:
    k = r["child_region"]
    if k in est:
        r["ins_ps"] = f"{float(r['ins_ps']) + (built[k] - est[k]) / 2 * 0.3659:.1f}"; print(k, built[k], r["ins_ps"])
w = csv.DictWriter(open(out, "w"), fieldnames=list(F[0].keys()), delimiter="\t"); w.writeheader(); w.writerows(F)
