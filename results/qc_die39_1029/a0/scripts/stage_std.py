"""DIE-QC-39 A0: measured FF/TT driver-stage delay (child input arrival - driver input arrival) on the kept V2 trees,
binned by driver fanout and leg length -> the 'standard stage' basis (mean / sd / n) for the estimate."""
import csv, sys, json, statistics as st, collections
D = sys.argv[1]
out = {}
for c in ("ff", "tt"):
    rows = []
    for t in ("nl", "nk"):
        T = {r["inst"]: r for r in csv.DictReader(open(f"{D}/{t}_tree_{c}.tsv"), delimiter="\t")}
        ch = collections.defaultdict(list)
        for r in T.values():
            if r["parent"] != "port:ck": ch[r["parent"]].append(r)
        for p, kids in ch.items():
            P = T[p]
            if P["kind"] != "node": continue
            buf = P["master"].startswith("BUF"); icg = P["master"].startswith("ICG")
            nodekids = [k for k in kids if k["kind"] == "node"]
            if len(nodekids) != len(kids): continue          # leaves (drive sinks) handled separately
            legs = [abs(float(k["x"]) - float(P["x"])) + abs(float(k["y"]) - float(P["y"])) for k in kids]
            for k, L in zip(kids, legs):
                rows.append(dict(t=t, typ="icg" if icg else "buf" if buf else P["master"], fo=len(kids), leg=L, lsum=sum(legs),
                                 lmax=max(legs), st=float(k["in_max_r"]) - float(P["in_max_r"]), mst=P["master"]))
    def summ(sel):
        v = [r["st"] for r in sel]
        return dict(n=len(v), mean=round(st.mean(v), 2), sd=round(st.pstdev(v), 2) if len(v) > 1 else 0,
                    p05=round(sorted(v)[int(0.05 * len(v))], 2), p95=round(sorted(v)[int(0.95 * len(v)) - 1], 2)) if v else dict(n=0)
    res = {}
    for typ in ("buf", "icg"):
        for fo in (1, 2, 3, 4):
            for lo, hi in ((0, 20), (20, 40), (40, 60), (60, 80), (80, 100), (100, 400)):
                sel = [r for r in rows if r["typ"] == typ and r["fo"] == fo and lo <= r["lmax"] < hi]
                if len(sel) >= 5: res[f"{typ}_fo{fo}_lmax{lo}-{hi}"] = summ(sel)
    # 'standard' windows as proposed: fo2 legs 40-60, fo1 legs 60-90
    res["STD_fo2_leg40-60"] = summ([r for r in rows if r["typ"] == "buf" and r["fo"] == 2 and all(40 <= x for x in [r["leg"]]) and r["lmax"] <= 60 and r["lsum"] >= 80])
    res["STD_fo1_leg60-90"] = summ([r for r in rows if r["typ"] == "buf" and r["fo"] == 1 and 60 <= r["leg"] <= 90])
    res["STD_fo1_leg40-60"] = summ([r for r in rows if r["typ"] == "buf" and r["fo"] == 1 and 40 <= r["leg"] <= 60])
    res["STD_fo1-2_leg40-90_all"] = summ([r for r in rows if r["typ"] == "buf" and r["fo"] <= 2 and 40 <= r["lmax"] <= 90])
    # linear fit st = a + b*leg + c*fo (buf, fo<=4, leg<=120)
    sel = [r for r in rows if r["typ"] == "buf" and r["fo"] <= 4 and r["lmax"] <= 120]
    import numpy as np
    X = np.array([[1, r["lmax"], r["fo"], r["lsum"]] for r in sel]); y = np.array([r["st"] for r in sel])
    b, *_ = np.linalg.lstsq(X, y, rcond=None); rms = float(np.sqrt(np.mean((X @ b - y) ** 2)))
    res["fit_buf_stage"] = dict(icpt=round(b[0], 3), per_um_lmax=round(b[1], 4), per_fanout=round(b[2], 3), per_um_lsum=round(b[3], 4), rms=round(rms, 2), n=len(sel))
    out[c] = res
json.dump(out, open(sys.argv[2], "w"), indent=1)
for c, res in out.items():
    print("==", c)
    for k, v in res.items(): print(f"  {k:28s} {v}")
